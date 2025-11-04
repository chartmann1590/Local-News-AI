package com.newsaiapp;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.widget.RemoteViews;
import android.widget.RemoteViewsService;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

public class NewsWidgetService extends RemoteViewsService {
    @Override
    public RemoteViewsFactory onGetViewFactory(Intent intent) {
        return new NewsRemoteViewsFactory(this.getApplicationContext(), intent);
    }
}

class NewsRemoteViewsFactory implements RemoteViewsService.RemoteViewsFactory {
    private Context context;
    private List<NewsItem> newsItems = new ArrayList<>();
    private static final String PREF_SERVER_IP = "flutter.server_ip";
    private static final String PREF_SERVER_PORT = "flutter.server_port";
    private static final String PREFS_NAME = "FlutterSharedPreferences";

    NewsRemoteViewsFactory(Context context, Intent intent) {
        this.context = context;
    }

    @Override
    public void onCreate() {
        // Fetch news data
        fetchNewsData();
    }

    @Override
    public void onDataSetChanged() {
        fetchNewsData();
    }

    private void fetchNewsData() {
        newsItems.clear();
        try {
            SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
            String serverIp = prefs.getString(PREF_SERVER_IP, null);
            String serverPort = prefs.getString(PREF_SERVER_PORT, "8000");
            
            if (serverIp == null || serverIp.isEmpty()) {
                return;
            }
            
            // Build base URL robustly (handle full URLs with or without port)
            String baseUrl = normalizeBaseUrl(serverIp, serverPort);
            if (baseUrl.isEmpty()) {
                return;
            }
            
            // Fetch articles
            String urlString = baseUrl + "/api/articles?page=1&limit=10";
            URL url = new URL(urlString);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(180000);
            conn.setReadTimeout(180000);
            
            if (conn.getResponseCode() == HttpURLConnection.HTTP_OK) {
                BufferedReader reader = new BufferedReader(
                    new InputStreamReader(conn.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }
                reader.close();
                
                JSONObject jsonResponse = new JSONObject(response.toString());
                JSONArray items = jsonResponse.optJSONArray("items");
                
                if (items != null) {
                    for (int i = 0; i < items.length(); i++) {
                        JSONObject item = items.getJSONObject(i);
                        NewsItem newsItem = new NewsItem();
                        newsItem.id = item.optInt("id", 0);
                        newsItem.title = item.optString("title", 
                            item.optString("source_title", "Untitled"));
                        // Prefer source_title, then source; sanitize literal "null"
                        String rawSource = item.optString("source_title", item.optString("source", ""));
                        if (rawSource == null || rawSource.equalsIgnoreCase("null")) {
                            rawSource = "";
                        }
                        newsItem.source = rawSource;
                        newsItem.imageUrl = item.optString("image_url", null);
                        // Try published_at first, then fetched_at, fallback to empty string
                        String pubAt = item.optString("published_at", null);
                        if (pubAt == null || pubAt.equalsIgnoreCase("null") || pubAt.isEmpty()) {
                            pubAt = item.optString("fetched_at", null);
                            if (pubAt == null || pubAt.equalsIgnoreCase("null") || pubAt.isEmpty()) {
                                pubAt = "";
                            }
                        }
                        newsItem.publishedAt = pubAt;
                        newsItems.add(newsItem);
                    }
                }
            }
            conn.disconnect();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private String normalizeBaseUrl(String serverIp, String serverPort) {
        String url = serverIp == null ? "" : serverIp.trim();
        if (url.isEmpty()) return "";
        boolean hasScheme = url.startsWith("http://") || url.startsWith("https://");
        if (!hasScheme) {
            url = "http://" + url;
        }
        try {
            java.net.URI uri = java.net.URI.create(url);
            if (uri.getPort() != -1) {
                return url;
            }
            if (serverPort != null && !serverPort.isEmpty()) {
                String scheme = uri.getScheme();
                String host = uri.getHost();
                String path = uri.getRawPath();
                if (path == null) path = "";
                return scheme + "://" + host + ":" + serverPort + path;
            }
            return url;
        } catch (Exception e) {
            return url;
        }
    }

    @Override
    public void onDestroy() {
        newsItems.clear();
    }

    @Override
    public int getCount() {
        return newsItems.size();
    }

    @Override
    public RemoteViews getViewAt(int position) {
        if (position >= newsItems.size()) {
            return null;
        }
        
        NewsItem item = newsItems.get(position);
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.news_widget_item);
        
        views.setTextViewText(R.id.news_title, item.title);
        if (item.source != null && !item.source.isEmpty()) {
            views.setTextViewText(R.id.news_source, item.source);
            views.setViewVisibility(R.id.news_source, android.view.View.VISIBLE);
        } else {
            views.setViewVisibility(R.id.news_source, android.view.View.GONE);
        }
        
        // Format date if available - check for null, empty, or literal "null" string
        String dateStr = null;
        if (item.publishedAt != null && !item.publishedAt.isEmpty() && !item.publishedAt.equalsIgnoreCase("null")) {
            try {
                // Try to parse ISO datetime string and format it with year and time
                // Handle various ISO formats: "yyyy-MM-ddTHH:mm:ss", "yyyy-MM-ddTHH:mm:ssZ", "yyyy-MM-ddTHH:mm:ss+00:00", etc.
                java.util.Date date = null;
                
                // First, try parsing with ISO 8601 using Java 8+ time API if available, fallback to SimpleDateFormat
                try {
                    // Try to parse as ISO 8601 with timezone
                    if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                        try {
                            java.time.Instant instant = java.time.Instant.parse(item.publishedAt);
                            date = java.util.Date.from(instant);
                        } catch (Exception e) {
                            // If that fails, try with offset datetime
                            try {
                                java.time.OffsetDateTime odt = java.time.OffsetDateTime.parse(item.publishedAt);
                                date = java.util.Date.from(odt.toInstant());
                            } catch (Exception e2) {
                                // Try with local datetime
                                try {
                                    java.time.LocalDateTime ldt = java.time.LocalDateTime.parse(item.publishedAt.substring(0, Math.min(19, item.publishedAt.length())));
                                    java.time.ZonedDateTime zdt = ldt.atZone(java.time.ZoneId.systemDefault());
                                    date = java.util.Date.from(zdt.toInstant());
                                } catch (Exception e3) {
                                    // Fall through to SimpleDateFormat parsing
                                }
                            }
                        }
                    }
                } catch (Exception e) {
                    // Continue to SimpleDateFormat parsing
                }
                
                // Fallback to SimpleDateFormat if Java 8+ time API not available or parsing failed
                if (date == null) {
                    String[] isoFormats = {
                        "yyyy-MM-dd'T'HH:mm:ss.SSSXXX",
                        "yyyy-MM-dd'T'HH:mm:ssXXX",
                        "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'",
                        "yyyy-MM-dd'T'HH:mm:ss'Z'",
                        "yyyy-MM-dd'T'HH:mm:ss",
                        "yyyy-MM-dd'T'HH:mm",
                        "yyyy-MM-dd"
                    };
                    
                    for (String format : isoFormats) {
                        try {
                            java.text.SimpleDateFormat inputFormat = new java.text.SimpleDateFormat(format, java.util.Locale.US);
                            // Set timezone for UTC if 'Z' is present
                            if (item.publishedAt.endsWith("Z") || format.contains("'Z'")) {
                                inputFormat.setTimeZone(java.util.TimeZone.getTimeZone("UTC"));
                            }
                            date = inputFormat.parse(item.publishedAt);
                            break;
                        } catch (Exception e) {
                            // Try next format
                            continue;
                        }
                    }
                }
                
                if (date != null) {
                    // Format as "MMM d, yyyy h:mm a" (e.g., "Jan 15, 2024 3:45 PM")
                    java.text.SimpleDateFormat outputFormat = new java.text.SimpleDateFormat("MMM d, yyyy h:mm a", java.util.Locale.US);
                    dateStr = outputFormat.format(date);
                } else {
                    // Fallback: try to extract at least date part
                    if (item.publishedAt.length() >= 10) {
                        try {
                            java.text.SimpleDateFormat inputFormat = new java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.US);
                            java.util.Date dateOnly = inputFormat.parse(item.publishedAt.substring(0, 10));
                            java.text.SimpleDateFormat outputFormat = new java.text.SimpleDateFormat("MMM d, yyyy", java.util.Locale.US);
                            dateStr = outputFormat.format(dateOnly);
                        } catch (Exception e) {
                            dateStr = item.publishedAt.substring(0, Math.min(16, item.publishedAt.length()));
                        }
                    } else {
                        dateStr = item.publishedAt;
                    }
                }
            } catch (Exception e) {
                dateStr = null;
            }
        }
        
        if (dateStr != null && !dateStr.isEmpty()) {
            views.setTextViewText(R.id.news_date, dateStr);
            views.setViewVisibility(R.id.news_date, android.view.View.VISIBLE);
        } else {
            views.setViewVisibility(R.id.news_date, android.view.View.GONE);
        }
        
        // Set click intent - opens app with deep link
        Intent fillInIntent = new Intent(context, MainActivity.class);
        fillInIntent.putExtra("article_id", item.id);
        fillInIntent.setAction(Intent.ACTION_VIEW);
        fillInIntent.setData(Uri.parse("news://article/" + item.id));
        views.setOnClickFillInIntent(R.id.news_item_container, fillInIntent);
        
        return views;
    }

    @Override
    public RemoteViews getLoadingView() {
        return null;
    }

    @Override
    public int getViewTypeCount() {
        return 1;
    }

    @Override
    public long getItemId(int position) {
        if (position < newsItems.size()) {
            return newsItems.get(position).id;
        }
        return position;
    }

    @Override
    public boolean hasStableIds() {
        return true;
    }
}

class NewsItem {
    int id;
    String title;
    String source;
    String imageUrl;
    String publishedAt;
}

