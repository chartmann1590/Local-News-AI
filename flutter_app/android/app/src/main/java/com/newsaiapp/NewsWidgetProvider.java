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
import android.widget.RemoteViewsService;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class NewsWidgetProvider extends AppWidgetProvider {
    private static final String PREF_SERVER_IP = "flutter.server_ip";
    private static final String PREF_SERVER_PORT = "flutter.server_port";
    private static final String PREFS_NAME = "FlutterSharedPreferences";
    
    @Override
    public void onUpdate(Context context, AppWidgetManager appWidgetManager, int[] appWidgetIds) {
        // Update each widget
        for (int appWidgetId : appWidgetIds) {
            updateAppWidget(context, appWidgetManager, appWidgetId);
        }
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        
        if (intent.getAction() != null && intent.getAction().equals(AppWidgetManager.ACTION_APPWIDGET_UPDATE)) {
            AppWidgetManager appWidgetManager = AppWidgetManager.getInstance(context);
            ComponentName thisWidget = new ComponentName(context, NewsWidgetProvider.class);
            int[] appWidgetIds = appWidgetManager.getAppWidgetIds(thisWidget);
            onUpdate(context, appWidgetManager, appWidgetIds);
        }
    }

    static void updateAppWidget(Context context, AppWidgetManager appWidgetManager, int appWidgetId) {
        // Set up the remote views service for the list
        Intent intent = new Intent(context, NewsWidgetService.class);
        intent.putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, appWidgetId);
        intent.setData(Uri.parse(intent.toUri(Intent.URI_INTENT_SCHEME)));
        
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.news_widget_layout);
        
        // Set up the RemoteViewsAdapter to handle the list
        views.setRemoteAdapter(R.id.news_list, intent);
        
        // Set empty view
        views.setEmptyView(R.id.news_list, R.id.empty_view);
        
        // Set pending intent template for list items - will be filled in by NewsWidgetService
        Intent clickIntent = new Intent(context, MainActivity.class);
        PendingIntent clickPendingIntent = PendingIntent.getActivity(
            context, 0, clickIntent, 
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        views.setPendingIntentTemplate(R.id.news_list, clickPendingIntent);
        
        // Refresh button
        Intent refreshIntent = new Intent(context, NewsWidgetProvider.class);
        refreshIntent.setAction(AppWidgetManager.ACTION_APPWIDGET_UPDATE);
        refreshIntent.putExtra(AppWidgetManager.EXTRA_APPWIDGET_IDS, new int[]{appWidgetId});
        PendingIntent refreshPendingIntent = PendingIntent.getBroadcast(
            context, 0, refreshIntent, 
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        views.setOnClickPendingIntent(R.id.refresh_button, refreshPendingIntent);
        
        // Open app button
        Intent openAppIntent = new Intent(context, MainActivity.class);
        openAppIntent.setAction("news://weather");
        PendingIntent openAppPendingIntent = PendingIntent.getActivity(
            context, 0, openAppIntent, 
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        views.setOnClickPendingIntent(R.id.open_app_button, openAppPendingIntent);
        
        appWidgetManager.updateAppWidget(appWidgetId, views);
        appWidgetManager.notifyAppWidgetViewDataChanged(appWidgetId, R.id.news_list);
    }

    @Override
    public void onEnabled(Context context) {
        // Schedule periodic updates every 30 minutes
        ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);
        scheduler.scheduleAtFixedRate(() -> {
            AppWidgetManager appWidgetManager = AppWidgetManager.getInstance(context);
            ComponentName thisWidget = new ComponentName(context, NewsWidgetProvider.class);
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

