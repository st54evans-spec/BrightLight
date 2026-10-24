package com.brightlight.glasses

import android.content.Context

/**
 * App settings. Only the bridge URL lives on the phone — your Anthropic/xAI API
 * keys stay on the bridge (its .env), never on the device.
 */
class Settings(context: Context) {
    private val prefs = context.getSharedPreferences("copilot", Context.MODE_PRIVATE)

    var bridgeUrl: String
        get() = prefs.getString(KEY_BRIDGE_URL, BuildConfig.BRIDGE_URL) ?: BuildConfig.BRIDGE_URL
        set(value) = prefs.edit().putString(KEY_BRIDGE_URL, value.trim()).apply()

    private companion object {
        const val KEY_BRIDGE_URL = "bridge_url"
    }
}
