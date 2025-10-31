package com.newsaiapp;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.widget.RemoteViews;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class WeatherWidgetProvider extends AppWidgetProvider {
    private static final String PREF_SERVER_IP = "flutter.server_ip";
    private static final String PREF_SERVER_PORT = "flutter.server_port";
    private static final String PREFS_NAME = "FlutterSharedPreferences";
    
    @Override
    public void onUpdate(Context context, AppWidgetManager appWidgetManager, int[] appWidgetIds) {
        // Show a lightweight loading state immediately and enqueue async update
        for (int appWidgetId : appWidgetIds) {
            RemoteViews loadingViews = new RemoteViews(context.getPackageName(), R.layout.weather_widget_layout);
            loadingViews.setTextViewText(R.id.location_text, "");
            loadingViews.setTextViewText(R.id.current_weather, "Loading…");
            loadingViews.setViewVisibility(R.id.forecast_container, android.view.View.GONE);
            loadingViews.setViewVisibility(R.id.radar_link, android.view.View.GONE);

            // Refresh and open app buttons wiring (same as final view)
            Intent refreshIntent = new Intent(context, WeatherWidgetProvider.class);
            refreshIntent.setAction(AppWidgetManager.ACTION_APPWIDGET_UPDATE);
            refreshIntent.putExtra(AppWidgetManager.EXTRA_APPWIDGET_IDS, new int[]{appWidgetId});
            PendingIntent refreshPendingIntent = PendingIntent.getBroadcast(
                context, 0, refreshIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            );
            loadingViews.setOnClickPendingIntent(R.id.refresh_button, refreshPendingIntent);

            Intent openAppIntent = new Intent(context, MainActivity.class);
            openAppIntent.setAction(Intent.ACTION_VIEW);
            openAppIntent.setData(Uri.parse("news://weather"));
            PendingIntent openAppPendingIntent = PendingIntent.getActivity(
                context, 0, openAppIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            );
            loadingViews.setOnClickPendingIntent(R.id.open_app_button, openAppPendingIntent);

            appWidgetManager.updateAppWidget(appWidgetId, loadingViews);

            // Enqueue background work to fetch and render
            WeatherWidgetUpdateService.enqueueWork(context, appWidgetId);
        }
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        
        if (intent.getAction() != null && intent.getAction().equals(AppWidgetManager.ACTION_APPWIDGET_UPDATE)) {
            AppWidgetManager appWidgetManager = AppWidgetManager.getInstance(context);
            ComponentName thisWidget = new ComponentName(context, WeatherWidgetProvider.class);
            int[] appWidgetIds = appWidgetManager.getAppWidgetIds(thisWidget);
            onUpdate(context, appWidgetManager, appWidgetIds);
        }
    }

    static void updateAppWidget(Context context, AppWidgetManager appWidgetManager, int appWidgetId) {
        // Kept for compatibility; actual content rendering is done in WeatherWidgetUpdateService
        // This method now simply enqueues a background refresh to avoid network on main thread
        WeatherWidgetUpdateService.enqueueWork(context, appWidgetId);
    }

    // Networking moved to WeatherWidgetUpdateService to avoid NetworkOnMainThreadException

    private static String getWeatherIcon(int code) {
        if (code == 0) return "☀️";
        if (code == 1 || code == 2) return "🌤️";
        if (code == 3) return "☁️";
        if (code == 45 || code == 48) return "🌫️";
        if (code >= 51 && code <= 57) return "🌦️";
        if (code >= 61 && code <= 67) return "🌧️";
        if (code >= 71 && code <= 86) return "❄️";
        if (code >= 80 && code <= 82) return "🌧️";
        if (code >= 95 && code <= 99) return "⛈️";
        return "🌡️";
    }

    @Override
    public void onEnabled(Context context) {
        // Schedule periodic updates every 30 minutes
        ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);
        scheduler.scheduleAtFixedRate(() -> {
            AppWidgetManager appWidgetManager = AppWidgetManager.getInstance(context);
            ComponentName thisWidget = new ComponentName(context, WeatherWidgetProvider.class);
            int[] appWidgetIds = appWidgetManager.getAppWidgetIds(thisWidget);
            if (appWidgetIds.length > 0) {
                onUpdate(context, appWidgetManager, appWidgetIds);
            }
        }, 0, 30, TimeUnit.MINUTES);
    }

    @Override
    public void onDisabled(Context context) {
        // Cleanup if needed
    }
}

class WeatherData {
    String location;
    String report;
    Double latitude;
    Double longitude;
    List<ForecastItem> dailyForecast;
    String currentTemp;
    String currentCondition;
    Integer currentWeatherCode;
}

class ForecastItem {
    String date;
    String maxTemp;
    String minTemp;
    String icon;
}

