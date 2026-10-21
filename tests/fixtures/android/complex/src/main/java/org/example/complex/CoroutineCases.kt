package org.example.complex

import kotlin.coroutines.resume
import kotlin.coroutines.suspendCoroutine

class CoroutineCases {
    suspend fun pause(value: String): String = suspendCoroutine { it.resume(value) }

    suspend fun workflow(value: String): String {
        val first = pause(value)
        return pause("COROUTINE_MARKER:" + first)
    }

    fun overload(value: Int): String = "R8_INTEGER:" + value
    fun overload(value: String): String = "R8_STRING:" + value
}
