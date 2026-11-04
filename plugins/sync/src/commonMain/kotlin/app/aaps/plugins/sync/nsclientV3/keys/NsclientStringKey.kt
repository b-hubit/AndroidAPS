package app.aaps.plugins.sync.nsclientV3.keys

import app.aaps.core.keys.interfaces.StringNonPreferenceKey
import app.aaps.core.nssdk.remotemodel.LastModified
import kotlinx.serialization.json.Json

/**
 * The per-collection "last modified" the v3 client uses to ask Nightscout what changed since its own
 * last visit. A cursor, so not exportable: another phone's timestamps would make this install skip
 * everything that changed in between, and those records would never be fetched again.
 *
 * If a key is ever added here that is NOT a cursor, give it `exportable = true` explicitly.
 */
enum class NsclientStringKey(
    override val key: String,
    override val defaultValue: String,
    override val exportable: Boolean = false
) : StringNonPreferenceKey {

    V3LastModified("ns_client_v3_last_modified", Json.encodeToString(LastModified.serializer(), LastModified(LastModified.Collections()))),

    /** b-hubit fork: how far the first load got, so a restart continues it instead of starting again. */
    V3FirstLoadContinue("ns_client_v3_first_load_continue", Json.encodeToString(LastModified.serializer(), LastModified(LastModified.Collections())))
}