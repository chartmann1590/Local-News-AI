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
                        newsItem.publishedAt = item.optString("published_at", 
                            item.optString("fetched_at", ""));
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
        
        // Format date if available
        if (item.publishedAt != null && !item.publishedAt.isEmpty()) {
            try {
                String dateStr = item.publishedAt.substring(0, Math.min(10, item.publishedAt.length()));
                views.setTextViewText(R.id.news_date, dateStr);
                views.setViewVisibility(R.id.news_date, android.view.View.VISIBLE);
            } catch (Exception e) {
                views.setViewVisibility(R.id.news_date, android.view.View.GONE);
            }
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

