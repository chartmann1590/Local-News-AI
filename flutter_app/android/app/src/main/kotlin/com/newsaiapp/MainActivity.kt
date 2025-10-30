package com.newsaiapp

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity: FlutterActivity() {
    private val CHANNEL = "com.newsaiapp/deep_link"
    private var pendingDeepLink: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        if (intent == null) return
        
        val action = intent.action
        val data = intent.data
        
        if (Intent.ACTION_VIEW == action && data != null) {
            val scheme = data.scheme
            val host = data.host
            val path = data.path
            
            when {
                scheme == "news" && host == "article" -> {
                    // Extract article ID from path (format: /123)
                    val articleId = path?.substringAfter("/")?.toIntOrNull()
                    if (articleId != null) {
                        pendingDeepLink = "news://article/$articleId"
                        // If Flutter engine is ready, send immediately
                        if (flutterEngine != null) {
                            sendDeepLinkToFlutter(pendingDeepLink!!)
                            pendingDeepLink = null
                        }
                    }
                }
                scheme == "news" && host == "weather" -> {
                    pendingDeepLink = "news://weather"
                    if (flutterEngine != null) {
                        sendDeepLinkToFlutter(pendingDeepLink!!)
                        pendingDeepLink = null
                    }
                }
            }
        }
        
        // Also check for article_id extra from widget clicks
        val articleId = intent.getIntExtra("article_id", -1)
        if (articleId != -1) {
            pendingDeepLink = "news://article/$articleId"
            if (flutterEngine != null) {
                sendDeepLinkToFlutter(pendingDeepLink!!)
                pendingDeepLink = null
            }
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            if (call.method == "getInitialDeepLink") {
                result.success(pendingDeepLink)
                pendingDeepLink = null
            } else {
                result.notImplemented()
            }
        }
        
        // Send pending deep link if any
        if (pendingDeepLink != null) {
            sendDeepLinkToFlutter(pendingDeepLink!!)
            pendingDeepLink = null
        }
    }

    private fun sendDeepLinkToFlutter(deepLink: String) {
        flutterEngine?.dartExecutor?.binaryMessenger?.let { messenger ->
            MethodChannel(messenger, CHANNEL).invokeMethod("handleDeepLink", deepLink)
        }
    }
}

