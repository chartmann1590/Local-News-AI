package com.newsaiapp;

import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.widget.RemoteViews;

import androidx.core.app.JobIntentService;

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

public class WeatherWidgetUpdateService extends JobIntentService {
    private static final int JOB_ID = 1001;
    private static final String EXTRA_APPWIDGET_ID = "extra_appwidget_id";

    private static final String PREF_SERVER_IP = "flutter.server_ip";
    private static final String PREF_SERVER_PORT = "flutter.server_port";
    private static final String PREFS_NAME = "FlutterSharedPreferences";

    public static void enqueueWork(Context context, int appWidgetId) {
        Intent work = new Intent(context, WeatherWidgetUpdateService.class);
        work.putExtra(EXTRA_APPWIDGET_ID, appWidgetId);
        enqueueWork(context, WeatherWidgetUpdateService.class, JOB_ID, work);
    }

    @Override
    protected void onHandleWork(Intent intent) {
        int appWidgetId = intent.getIntExtra(EXTRA_APPWIDGET_ID, AppWidgetManager.INVALID_APPWIDGET_ID);
        AppWidgetManager appWidgetManager = AppWidgetManager.getInstance(this);

        if (appWidgetId == AppWidgetManager.INVALID_APPWIDGET_ID) {
            // Fallback: update all instances
            ComponentName thisWidget = new ComponentName(this, WeatherWidgetProvider.class);
            int[] ids = appWidgetManager.getAppWidgetIds(thisWidget);
            for (int id : ids) {
                updateOne(id, appWidgetManager);
            }
        } else {
            updateOne(appWidgetId, appWidgetManager);
        }
    }

    private void updateOne(int appWidgetId, AppWidgetManager appWidgetManager) {
        Context context = this;
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.weather_widget_layout);

        try {
            // Initialize with default values
            views.setTextViewText(R.id.location_text, "");
            views.setTextViewText(R.id.current_weather, "");
            views.setViewVisibility(R.id.forecast_container, android.view.View.GONE);
            views.setViewVisibility(R.id.radar_link, android.view.View.GONE);

            WeatherData data = fetchWeatherData(context);

            if (data == null) {
                SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
                String serverIp = prefs.getString(PREF_SERVER_IP, null);
                if (serverIp == null || serverIp.isEmpty()) {
                    views.setTextViewText(R.id.current_weather, "Configure server in app");
                } else {
                    views.setTextViewText(R.id.current_weather, "Unable to load weather");
                }
            } else {
                if (data.location != null) {
                    views.setTextViewText(R.id.location_text, data.location);
                }
                
                // Build current weather display
                StringBuilder currentInfo = new StringBuilder();
                
                // If we have current weather data, show it
                if (data.currentTemp != null && !data.currentTemp.isEmpty()) {
                    String tempStr = data.currentTemp;
                    // Remove decimal if it's .0
                    if (tempStr.endsWith(".0")) {
                        tempStr = tempStr.substring(0, tempStr.length() - 2);
                    }
                    currentInfo.append(data.currentCondition != null ? data.currentCondition + " " : "");
                    currentInfo.append(tempStr).append("°");
                    
                    // Optionally append the report if it exists (first sentence or first 50 chars)
                    if (data.report != null && !data.report.isEmpty()) {
                        String reportText = data.report.trim();
                        // Try to get first sentence
                        int periodIndex = reportText.indexOf('.');
                        int commaIndex = reportText.indexOf(',');
                        int cutoffIndex = Math.min(
                            periodIndex > 0 ? periodIndex : Integer.MAX_VALUE,
                            commaIndex > 0 ? commaIndex : Integer.MAX_VALUE
                        );
                        if (cutoffIndex < Integer.MAX_VALUE && cutoffIndex < 80) {
                            currentInfo.append("\n").append(reportText.substring(0, Math.min(cutoffIndex + 1, 80)));
                        } else if (reportText.length() > 0) {
                            currentInfo.append("\n").append(reportText.substring(0, Math.min(50, reportText.length())));
                        }
                    }
                } else if (data.report != null && !data.report.isEmpty()) {
                    // Fallback to report if no current weather data
                    String reportText = data.report;
                    if (reportText.length() > 100) {
                        reportText = reportText.substring(0, 100) + "...";
                    }
                    currentInfo.append(reportText);
                }
                
                if (currentInfo.length() > 0) {
                    views.setTextViewText(R.id.current_weather, currentInfo.toString());
                } else {
                    views.setTextViewText(R.id.current_weather, "Weather data unavailable");
                }

                if (data.dailyForecast != null && !data.dailyForecast.isEmpty()) {
                    views.setViewVisibility(R.id.forecast_container, android.view.View.VISIBLE);
                    views.removeAllViews(R.id.forecast_container);

                    int maxItems = Math.min(5, data.dailyForecast.size());
                    for (int i = 0; i < maxItems; i++) {
                        ForecastItem item = data.dailyForecast.get(i);
                        RemoteViews itemView = new RemoteViews(context.getPackageName(), R.layout.weather_widget_forecast_item);
                        try {
                            SimpleDateFormat inputFormat = new SimpleDateFormat("yyyy-MM-dd", Locale.getDefault());
                            SimpleDateFormat outputFormat = new SimpleDateFormat("EEE M/d", Locale.getDefault());
                            Date date = inputFormat.parse(item.date);
                            itemView.setTextViewText(R.id.forecast_date, outputFormat.format(date));
                        } catch (Exception e) {
                            itemView.setTextViewText(R.id.forecast_date, item.date);
                        }
                        itemView.setTextViewText(R.id.forecast_icon, item.icon);
                        itemView.setTextViewText(R.id.forecast_high, "H:" + item.maxTemp + "°");
                        itemView.setTextViewText(R.id.forecast_low, "L:" + item.minTemp + "°");
                        views.addView(R.id.forecast_container, itemView);
                    }
                } else {
                    views.setViewVisibility(R.id.forecast_container, android.view.View.GONE);
                }

                if (data.latitude != null && data.longitude != null) {
                    views.setViewVisibility(R.id.radar_link, android.view.View.VISIBLE);
                    views.setTextViewText(R.id.radar_link, "View Radar Map →");
                } else {
                    views.setViewVisibility(R.id.radar_link, android.view.View.GONE);
                }
            }

        // Wire up buttons
        Intent refreshIntent = new Intent(context, WeatherWidgetProvider.class);
        refreshIntent.setAction(AppWidgetManager.ACTION_APPWIDGET_UPDATE);
        refreshIntent.putExtra(AppWidgetManager.EXTRA_APPWIDGET_IDS, new int[]{appWidgetId});
        views.setOnClickPendingIntent(R.id.refresh_button, android.app.PendingIntent.getBroadcast(
            context, 0, refreshIntent,
            android.app.PendingIntent.FLAG_UPDATE_CURRENT | android.app.PendingIntent.FLAG_IMMUTABLE
        ));

        Intent openAppIntent = new Intent(context, MainActivity.class);
        openAppIntent.setAction(Intent.ACTION_VIEW);
        openAppIntent.setData(Uri.parse("news://weather"));
        views.setOnClickPendingIntent(R.id.open_app_button, android.app.PendingIntent.getActivity(
            context, 0, openAppIntent,
            android.app.PendingIntent.FLAG_UPDATE_CURRENT | android.app.PendingIntent.FLAG_IMMUTABLE
        ));
        views.setOnClickPendingIntent(R.id.radar_link, android.app.PendingIntent.getActivity(
            context, 0, openAppIntent,
            android.app.PendingIntent.FLAG_UPDATE_CURRENT | android.app.PendingIntent.FLAG_IMMUTABLE
        ));

        } catch (Exception e) {
            // Ensure widget is updated even if there's an error
            views.setTextViewText(R.id.current_weather, "Error: " + e.getMessage());
            e.printStackTrace();
        } finally {
            // Always update the widget, even if there was an error
            appWidgetManager.updateAppWidget(appWidgetId, views);
        }
    }

    private WeatherData fetchWeatherData(Context context) {
        WeatherData data = new WeatherData();
        try {
            SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
            String serverIp = prefs.getString(PREF_SERVER_IP, null);
            String serverPort = prefs.getString(PREF_SERVER_PORT, "8000");

            if (serverIp == null || serverIp.isEmpty()) {
                android.util.Log.w("WeatherWidget", "Server IP not configured");
                return null;
            }

            String baseUrl = normalizeBaseUrl(serverIp, serverPort);
            if (baseUrl.isEmpty()) {
                android.util.Log.w("WeatherWidget", "Failed to normalize base URL from IP: " + serverIp + ", Port: " + serverPort);
                return null;
            }

            String urlString = baseUrl + "/api/weather";
            android.util.Log.d("WeatherWidget", "Fetching weather from: " + urlString);
            URL url = new URL(urlString);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(10000);

            int responseCode = conn.getResponseCode();
            android.util.Log.d("WeatherWidget", "Response code: " + responseCode);
            
            if (responseCode == HttpURLConnection.HTTP_OK) {
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }
                reader.close();

                JSONObject jsonResponse = new JSONObject(response.toString());
                data.location = jsonResponse.optString("location", null);
                data.report = jsonResponse.optString("report", null);
                data.latitude = jsonResponse.optDouble("latitude", Double.NaN);
                if (Double.isNaN(data.latitude)) data.latitude = null;
                data.longitude = jsonResponse.optDouble("longitude", Double.NaN);
                if (Double.isNaN(data.longitude)) data.longitude = null;

                JSONObject forecast = jsonResponse.optJSONObject("forecast");
                if (forecast != null) {
                    // Extract current weather data
                    JSONObject currentWeather = forecast.optJSONObject("current_weather");
                    if (currentWeather != null) {
                        data.currentTemp = currentWeather.optString("temperature", null);
                        data.currentCondition = getWeatherIcon(currentWeather.optInt("weathercode", 0));
                        data.currentWeatherCode = currentWeather.optInt("weathercode", 0);
                    }
                    
                    JSONObject daily = forecast.optJSONObject("daily");
                    if (daily != null) {
                        JSONArray times = daily.optJSONArray("time");
                        JSONArray maxTemps = daily.optJSONArray("temperature_2m_max");
                        JSONArray minTemps = daily.optJSONArray("temperature_2m_min");
                        JSONArray codes = daily.optJSONArray("weathercode");
                        data.dailyForecast = new ArrayList<>();
                        if (times != null && maxTemps != null && minTemps != null && codes != null) {
                            int maxItems = Math.min(5, Math.min(times.length(), Math.min(maxTemps.length(), Math.min(minTemps.length(), codes.length()))));
                            for (int i = 0; i < maxItems; i++) {
                                ForecastItem item = new ForecastItem();
                                item.date = times.optString(i, "");
                                item.maxTemp = maxTemps.optString(i, "");
                                item.minTemp = minTemps.optString(i, "");
                                int code = codes.optInt(i, 0);
                                item.icon = getWeatherIcon(code);
                                data.dailyForecast.add(item);
                            }
                        }
                    }
                }
            } else {
                android.util.Log.w("WeatherWidget", "HTTP error: " + responseCode);
                // Try to read error stream for debugging
                try {
                    java.io.InputStream errorStream = conn.getErrorStream();
                    if (errorStream != null) {
                        BufferedReader errorReader = new BufferedReader(new InputStreamReader(errorStream));
                        StringBuilder errorResponse = new StringBuilder();
                        String errorLine;
                        while ((errorLine = errorReader.readLine()) != null) {
                            errorResponse.append(errorLine);
                        }
                        errorReader.close();
                        android.util.Log.w("WeatherWidget", "Error response: " + errorResponse.toString());
                    }
                } catch (Exception ignored) {}
            }
            conn.disconnect();
        } catch (java.net.SocketTimeoutException e) {
            android.util.Log.e("WeatherWidget", "Timeout fetching weather", e);
            return null;
        } catch (java.net.UnknownHostException e) {
            android.util.Log.e("WeatherWidget", "Unknown host", e);
            return null;
        } catch (java.io.IOException e) {
            android.util.Log.e("WeatherWidget", "IO error fetching weather", e);
            return null;
        } catch (Exception e) {
            android.util.Log.e("WeatherWidget", "Error fetching weather", e);
            e.printStackTrace();
            return null;
        }
        return data;
    }

    private String normalizeBaseUrl(String serverIp, String serverPort) {
        String url = serverIp == null ? "" : serverIp.trim();
        if (url.isEmpty()) return "";
        
        // Remove any existing protocol
        boolean hasScheme = url.startsWith("http://") || url.startsWith("https://");
        String cleanUrl = url;
        if (hasScheme) {
            cleanUrl = url.replaceFirst("https?://", "");
        }
        
        // Extract host and port if URL contains a colon (might be host:port or full URL)
        String host = cleanUrl;
        String existingPort = null;
        int colonIndex = cleanUrl.indexOf(':');
        if (colonIndex > 0) {
            host = cleanUrl.substring(0, colonIndex);
            String afterColon = cleanUrl.substring(colonIndex + 1);
            // Check if it's a port number or part of a path
            if (afterColon.length() > 0 && Character.isDigit(afterColon.charAt(0))) {
                int slashIndex = afterColon.indexOf('/');
                if (slashIndex > 0) {
                    existingPort = afterColon.substring(0, slashIndex);
                } else {
                    existingPort = afterColon;
                }
            }
        }
        
        // Remove any path components from the host
        int slashIndex = host.indexOf('/');
        if (slashIndex > 0) {
            host = host.substring(0, slashIndex);
        }
        
        // Use existing port if present, otherwise use provided serverPort
        String portToUse = (existingPort != null && !existingPort.isEmpty()) ? existingPort : serverPort;
        
        // Build the final URL
        try {
            if (portToUse != null && !portToUse.isEmpty()) {
                return "http://" + host + ":" + portToUse;
            } else {
                return "http://" + host;
            }
        } catch (Exception e) {
            android.util.Log.e("WeatherWidget", "Error normalizing URL", e);
            // Fallback: try simple approach
            if (!hasScheme) {
                url = "http://" + url;
            }
            return url;
        }
    }

    private String getWeatherIcon(int code) {
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
}


