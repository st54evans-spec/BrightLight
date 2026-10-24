package com.brightlight.glasses

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Talks to the TypeScript brain bridge (npm run serve). All crew/greeting/persona
 * logic lives on the bridge; this client just posts transcripts and reads back
 * what to do. No API keys on the glasses or the phone.
 */
class BridgeClient(private val baseUrl: String) {

    sealed class AskResult {
        data class Greeting(val memberId: String, val name: String, val greeting: String) : AskResult()
        data class NeedImage(val memberId: String, val name: String, val prompt: String) : AskResult()
        data class Answer(val memberId: String, val name: String, val answer: String) : AskResult()
        data class Failure(val message: String) : AskResult()
    }

    data class CrewMember(val id: String, val name: String, val greeting: String, val provider: String)

    suspend fun crew(): List<CrewMember> = withContext(Dispatchers.IO) {
        val body = httpGet("/crew")
        val arr = JSONObject(body).getJSONArray("members")
        (0 until arr.length()).map { i ->
            val m = arr.getJSONObject(i)
            CrewMember(m.getString("id"), m.getString("name"), m.getString("greeting"), m.getString("provider"))
        }
    }

    /** Send a transcript. Optionally attach a captured frame + the member to answer as. */
    suspend fun ask(text: String, memberId: String? = null, imageBase64: String? = null): AskResult =
        withContext(Dispatchers.IO) {
            val payload = JSONObject().put("text", text)
            if (memberId != null) payload.put("memberId", memberId)
            if (imageBase64 != null) payload.put("imageBase64", imageBase64)

            try {
                val res = JSONObject(httpPost("/ask", payload.toString()))
                when (res.optString("status")) {
                    "greeting" -> AskResult.Greeting(res.getString("member"), res.getString("name"), res.getString("greeting"))
                    "need_image" -> AskResult.NeedImage(res.getString("member"), res.getString("name"), res.getString("prompt"))
                    "answer" -> AskResult.Answer(res.getString("member"), res.getString("name"), res.getString("answer"))
                    else -> AskResult.Failure(res.optString("error", "Unexpected bridge response"))
                }
            } catch (e: Exception) {
                AskResult.Failure(e.message ?: "bridge error")
            }
        }

    private fun httpGet(path: String): String = openConn(path, "GET").run {
        try { readBody(this) } finally { disconnect() }
    }

    private fun httpPost(path: String, json: String): String = openConn(path, "POST").run {
        try {
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
            outputStream.use { it.write(json.toByteArray()) }
            readBody(this)
        } finally { disconnect() }
    }

    private fun openConn(path: String, method: String): HttpURLConnection =
        (URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 8000
            readTimeout = 30000
        }

    private fun readBody(conn: HttpURLConnection): String {
        val stream = if (conn.responseCode in 200..299) conn.inputStream else conn.errorStream
        return stream?.bufferedReader()?.use { it.readText() } ?: ""
    }
}
