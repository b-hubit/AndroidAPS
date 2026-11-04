package app.aaps.implementation.logging

import app.aaps.core.interfaces.logging.AAPSLogger
import app.aaps.core.interfaces.logging.L
import app.aaps.core.interfaces.logging.LTag
import kotlinx.cinterop.ExperimentalForeignApi
import platform.Foundation.NSDate
import platform.Foundation.NSDocumentDirectory
import platform.Foundation.NSFileHandle
import platform.Foundation.NSFileManager
import platform.Foundation.NSISO8601DateFormatter
import platform.Foundation.NSLog
import platform.Foundation.NSSearchPathForDirectoriesInDomains
import platform.Foundation.NSString
import platform.Foundation.NSURL
import platform.Foundation.NSUTF8StringEncoding
import platform.Foundation.NSUserDomainMask
import platform.Foundation.closeFile
import platform.Foundation.create
import platform.Foundation.dataUsingEncoding
import platform.Foundation.fileHandleForWritingAtPath
import platform.Foundation.seekToEndOfFile
import platform.Foundation.writeData
import kotlin.concurrent.atomics.AtomicBoolean
import kotlin.concurrent.atomics.ExperimentalAtomicApi
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.IO
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.launch

/**
 * Logging on iOS: the console for looking at now, a file for looking at later.
 *
 * The Android logger goes through logback, which is a JVM library, so iOS needs its own. Two sinks,
 * because the two questions are different. `NSLog` answers "what is happening" - it reaches the
 * unified log, so it shows up under `xcrun simctl launch --console`, in Console.app, and in a device
 * log. The file answers "what happened", which matters most for a diabetes app: by the time a user
 * reports something odd, the console is long gone.
 *
 * `os_log` would be the better console sink, but it is a C macro rather than a function, so
 * Kotlin/Native exposes `os_log_create` and `OS_LOG_DEFAULT` with nothing to call them with.
 * `NSLog` ends up in the same unified log.
 *
 * ## What this does not do yet
 *
 * Rotation is by size and keeps one previous file, so a run cannot fill the device. It does not zip
 * and it does not keep a dated history, which the Android side does - that belongs with whatever
 * ends up sharing logs off the phone, and there is no such path on iOS yet.
 */
@OptIn(ExperimentalForeignApi::class)
class AAPSLoggerIos(
    private val fileName: String = "aaps.log",
    private val maxBytes: Long = 5L * 1024 * 1024,
    /** Reads the stored per-tag switches. Null before the graph can supply one - see [enabled]. */
    private val logConfig: (() -> L)? = null
) : AAPSLogger {

    private val timestamps = NSISO8601DateFormatter()

    // ---------------------------------------------------------------------------------------------
    // AAPSLogger
    // ---------------------------------------------------------------------------------------------

    override fun debug(message: String) = write("DEBUG", null, message)
    override fun debug(enable: Boolean, tag: LTag, message: String) {
        if (enable) write("DEBUG", tag, message)
    }

    override fun debug(tag: LTag, message: String) = write("DEBUG", tag, message)
    override fun debug(tag: LTag, accessor: () -> String) = write("DEBUG", tag, accessor())
    override fun debug(tag: LTag, format: String, vararg arguments: Any?) = write("DEBUG", tag, format.fill(arguments))

    override fun info(tag: LTag, message: String) = write("INFO", tag, message)
    override fun info(tag: LTag, format: String, vararg arguments: Any?) = write("INFO", tag, format.fill(arguments))

    override fun warn(tag: LTag, message: String) = write("WARN", tag, message)
    override fun warn(tag: LTag, format: String, vararg arguments: Any?) = write("WARN", tag, format.fill(arguments))

    override fun error(tag: LTag, message: String) = write("ERROR", tag, message, gated = false)
    override fun error(tag: LTag, message: String, throwable: Throwable) =
        write("ERROR", tag, "$message\n${throwable.stackTraceToString()}", gated = false)

    override fun error(tag: LTag, format: String, vararg arguments: Any?) = write("ERROR", tag, format.fill(arguments), gated = false)
    override fun error(message: String) = write("ERROR", null, message, gated = false)
    override fun error(message: String, throwable: Throwable) =
        write("ERROR", null, "$message\n${throwable.stackTraceToString()}", gated = false)

    override fun error(format: String, vararg arguments: Any?) = write("ERROR", null, format.fill(arguments), gated = false)

    override fun debug(className: String, methodName: String, lineNumber: Int, tag: LTag, message: String) =
        write("DEBUG", tag, "$className.$methodName($lineNumber): $message")

    override fun info(className: String, methodName: String, lineNumber: Int, tag: LTag, message: String) =
        write("INFO", tag, "$className.$methodName($lineNumber): $message")

    override fun warn(className: String, methodName: String, lineNumber: Int, tag: LTag, message: String) =
        write("WARN", tag, "$className.$methodName($lineNumber): $message")

    override fun error(className: String, methodName: String, lineNumber: Int, tag: LTag, message: String) =
        write("ERROR", tag, "$className.$methodName($lineNumber): $message", gated = false)

    // ---------------------------------------------------------------------------------------------
    // Sinks
    // ---------------------------------------------------------------------------------------------

    /**
     * Whether [tag] is switched on, from the stored preference when there is one.
     *
     * This used to read `tag.defaultValue`, which is the compile-time default and not a switch at
     * all: eight tags ship `false`, so they could never be turned on however the log-settings sheet
     * was set, and "enable NSCLIENT_SYNC and send me the log" was impossible off Android. The
     * preference-backed answer is `L`, which lives in `shared/impl` commonMain and is available on
     * every platform.
     *
     * Deferred and nullable because this logger is one of the first things the graph builds - the
     * probe shell and the tests construct it with no graph at all - and `L` needs `Preferences`.
     * Before it can be read, the compile-time default is the only answer there is.
     */
    internal fun enabled(tag: LTag): Boolean =
        logConfig?.let { runCatching { it().findByName(tag.tag).enabled }.getOrNull() } ?: tag.defaultValue

    private fun write(level: String, tag: LTag?, message: String, gated: Boolean = true) {
        // Errors are never gated, matching Android: a tag switched off must quieten the running
        // commentary, not hide the thing that went wrong. This gated everything, so an error on one
        // of the tags that ship disabled was dropped and nothing recorded that it had been.
        if (gated && tag != null && !enabled(tag)) return

        val line = "${timestamps.stringFromDate(NSDate())} $level ${tag?.tag ?: "CORE"}: $message"
        // b-hubit fork: the console gets warnings and errors only. NSLog is
        // synchronous and slow, and it ran for every debug line on the thread doing the work - during a
        // sync that is tens of thousands of lines. The file below still gets every line.
        // NSLog is a C varargs function, so `%@` needs a real Obj-C object. Passing the Kotlin
        // String straight through segfaults - it is not boxed into an NSString on the way.
        if (level == "ERROR" || level == "WARN") NSLog("%@", NSString.create(string = line))
        logPath()?.let { LogFileWriter.forPath(it, maxBytes).enqueue(line) }
    }

    /**
     * `{}` placeholders, as logback spells them.
     *
     * Callers write the slf4j style the Android logger accepts, so the same call has to mean the
     * same thing here. Extra arguments are dropped and missing ones are left as `{}`, which is what
     * logback does rather than throwing - a broken log line must never take the app down.
     */
    internal fun String.fill(arguments: Array<out Any?>): String {
        val out = StringBuilder()
        // Scans forward rather than searching the result again each time. Re-searching meant an
        // argument that itself contained "{}" was treated as the next placeholder, so it swallowed
        // the argument after it.
        var from = 0
        for (argument in arguments) {
            val at = indexOf("{}", from)
            if (at < 0) break
            out.append(this, from, at).append(argument.toString())
            from = at + 2
        }
        out.append(this, from, length)
        return out.toString()
    }

    /**
     * Writes log lines in the background, one writer per file.
     *
     * b-hubit fork. Each line used to look the file's size up, open it, seek to the
     * end, write and close it, synchronously on the calling thread. Now lines go into a queue and one
     * background coroutine writes whatever has gathered in one go, through a handle that stays open.
     * One writer per path, because two loggers write the same `aaps.log` (the graph's and the settings
     * store's) and two open handles would overwrite each other's lines.
     */
    private class LogFileWriter(private val path: String, private val maxBytes: Long) {

        private val lines = Channel<String>(Channel.UNLIMITED)
        private var handle: NSFileHandle? = null
        private var written = 0L

        init {
            CoroutineScope(Dispatchers.IO.limitedParallelism(1) + SupervisorJob()).launch {
                val batch = StringBuilder()
                for (first in lines) {
                    batch.append(first).append('\n')
                    // Everything already queued goes out in the same write.
                    while (batch.length < BATCH_CHARS) {
                        val next = lines.tryReceive().getOrNull() ?: break
                        batch.append(next).append('\n')
                    }
                    runCatching { write(batch.toString()) }
                    batch.clear()
                }
            }
        }

        fun enqueue(line: String) {
            lines.trySend(line)
        }

        private fun write(text: String) {
            val data = NSString.create(string = text).dataUsingEncoding(NSUTF8StringEncoding) ?: return
            val out = handle ?: open() ?: return
            out.writeData(data)
            written += data.length.toLong()
            if (written >= maxBytes) rotate()
        }

        private fun open(): NSFileHandle? {
            val manager = NSFileManager.defaultManager
            if (!manager.fileExistsAtPath(path)) manager.createFileAtPath(path, null, null)
            written = (manager.attributesOfItemAtPath(path, null)?.get("NSFileSize") as? Number)?.toLong() ?: 0L
            if (written >= maxBytes) {
                rotateFile(manager)
                manager.createFileAtPath(path, null, null)
                written = 0L
            }
            return NSFileHandle.fileHandleForWritingAtPath(path)?.also {
                it.seekToEndOfFile()
                handle = it
            }
        }

        /** Keeps one previous file, so the worst case on disk is twice [maxBytes]. */
        private fun rotate() {
            handle?.closeFile()
            handle = null
            rotateFile(NSFileManager.defaultManager)
        }

        private fun rotateFile(manager: NSFileManager) {
            val previous = "$path.1"
            manager.removeItemAtPath(previous, null)
            manager.moveItemAtPath(path, previous, null)
        }

        companion object {
            private const val BATCH_CHARS = 64 * 1024
            private val writers = mutableMapOf<String, LogFileWriter>()
            @OptIn(ExperimentalAtomicApi::class)
            private val lock = AtomicBoolean(false)

            @OptIn(ExperimentalAtomicApi::class)
            fun forPath(path: String, maxBytes: Long): LogFileWriter {
                // A spin lock rather than `synchronized`, which is JVM only. Held for a map lookup.
                while (!lock.compareAndSet(false, true)) Unit
                try {
                    return writers.getOrPut(path) { LogFileWriter(path, maxBytes) }
                } finally {
                    lock.store(false)
                }
            }
        }
    }

    private fun logPath(): String? {
        val documents = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, true)
            .firstOrNull() as? String ?: return null
        return "$documents/$fileName"
    }

    /** Where the log file is, so the app can offer it for sharing once there is a way to. */
    fun logFileUrl(): NSURL? = logPath()?.let { NSURL.fileURLWithPath(it) }
}
