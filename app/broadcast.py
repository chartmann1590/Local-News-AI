from __future__ import annotations

import os
import io
import json
import logging
import math
import tempfile
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

import requests
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips,
    CompositeVideoClip, CompositeAudioClip, TextClip, VideoFileClip, transfx, vfx,
    ColorClip
)
from moviepy.audio.fx.all import audio_loop
from PIL import Image, ImageDraw, ImageFont

from .database import SessionLocal
from .models import Article, WeatherReport, Broadcast, TTSSettings, AppSettings
from .ai import _post_ollama, DEFAULT_OLLAMA_BASE_URL, DEFAULT_OLLAMA_MODEL
from .tts import TTSClient, DEFAULT_TTS_BASE
from .geo import get_local_now

logger = logging.getLogger("app.broadcast")


def _ensure_broadcast_dirs() -> Tuple[str, str]:
    """Ensure broadcast directories exist. Returns (base_dir, images_dir)."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "broadcasts"))
    images_dir = os.path.join(base_dir, "images")
    for d in [base_dir, images_dir]:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
    return base_dir, images_dir


def download_reporter_gif(output_path: str) -> bool:
    """Download a free animated GIF of a woman news reporter if not already present."""
    if os.path.exists(output_path):
        logger.info(f"Reporter GIF already exists: {output_path}")
        return True
    
    try:
        # Try to download from a free GIF source (Giphy, Tenor, etc.)
        # Using a direct link to a free-to-use animated GIF
        # Note: This is a placeholder - you may want to use a specific free GIF URL
        gif_urls = [
            # Example free GIF URLs - replace with actual free-to-use news reporter GIFs
            # These are placeholder URLs - you'll need actual free GIF URLs
            "https://media.giphy.com/media/example.gif",  # Replace with actual URL
        ]
        
        # For now, we'll create a simple animated GIF using PIL
        # This creates a basic animated avatar as a fallback
        logger.info("Creating animated reporter GIF")
        
        # Create a simple animated GIF with a few frames showing a talking animation
        frames = []
        for i in range(8):  # 8 frames for animation
            img = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            center = (100, 100)
            radius = 80
            
            # Outer circle (border)
            draw.ellipse(
                [(center[0] - radius, center[1] - radius), (center[0] + radius, center[1] + radius)],
                fill='#1e40af',
                outline='#ffffff',
                width=4
            )
            
            # Inner circle (face)
            inner_radius = radius - 20
            draw.ellipse(
                [(center[0] - inner_radius, center[1] - inner_radius), 
                 (center[0] + inner_radius, center[1] + inner_radius)],
                fill='#fbbf24',
                outline='#d97706',
                width=2
            )
            
            # Animated mouth (talking effect)
            mouth_open = (i % 4) < 2  # Alternate open/closed
            eye_y = center[1] - 15
            eye_size = 8
            
            # Eyes
            draw.ellipse(
                [(center[0] - 25 - eye_size, eye_y - eye_size), 
                 (center[0] - 25 + eye_size, eye_y + eye_size)],
                fill='#1f2937'
            )
            draw.ellipse(
                [(center[0] + 25 - eye_size, eye_y - eye_size), 
                 (center[0] + 25 + eye_size, eye_y + eye_size)],
                fill='#1f2937'
            )
            
            # Animated mouth
            mouth_y = center[1] + 20
            if mouth_open:
                # Open mouth (oval)
                draw.ellipse(
                    [(center[0] - 15, mouth_y - 8), (center[0] + 15, mouth_y + 8)],
                    fill='#1f2937'
                )
            else:
                # Closed mouth (smile arc)
                draw.arc(
                    [(center[0] - 30, mouth_y - 15), (center[0] + 30, mouth_y + 15)],
                    start=0,
                    end=180,
                    fill='#1f2937',
                    width=3
                )
            
            # Professional label
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            except Exception:
                font = ImageFont.load_default()
            
            label = "REPORTER"
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = center[0] - text_width // 2
            text_y = center[1] + radius - 10
            
            draw.rectangle(
                [(text_x - 5, text_y - 3), (text_x + text_width + 5, text_y + (bbox[3] - bbox[1]) + 3)],
                fill='#1e40af',
                outline='#ffffff',
                width=1
            )
            draw.text((text_x, text_y), label, fill='#ffffff', font=font)
            
            frames.append(img)
        
        # Save as animated GIF
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=200,  # 200ms per frame (5 fps)
            loop=0,  # Loop forever
            format='GIF'
        )
        
        logger.info(f"Created animated reporter GIF: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create/download reporter GIF: {e}", exc_info=True)
        return False


def create_reporter_avatar(output_path: str, width: int = 200, height: int = 200) -> bool:
    """Create a simple reporter avatar image for the talking head overlay."""
    try:
        # Create a circular avatar with a professional look
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw circular background (professional blue-gray)
        center = (width // 2, height // 2)
        radius = min(width, height) // 2 - 10
        
        # Outer circle (border)
        draw.ellipse(
            [(center[0] - radius, center[1] - radius), (center[0] + radius, center[1] + radius)],
            fill='#1e40af',  # Blue
            outline='#ffffff',
            width=4
        )
        
        # Inner circle (face)
        inner_radius = radius - 20
        draw.ellipse(
            [(center[0] - inner_radius, center[1] - inner_radius), 
             (center[0] + inner_radius, center[1] + inner_radius)],
            fill='#fbbf24',  # Light skin tone
            outline='#d97706',
            width=2
        )
        
        # Simple face features
        # Eyes
        eye_y = center[1] - 15
        eye_size = 8
        draw.ellipse(
            [(center[0] - 25 - eye_size, eye_y - eye_size), 
             (center[0] - 25 + eye_size, eye_y + eye_size)],
            fill='#1f2937'
        )
        draw.ellipse(
            [(center[0] + 25 - eye_size, eye_y - eye_size), 
             (center[0] + 25 + eye_size, eye_y + eye_size)],
            fill='#1f2937'
        )
        
        # Smile
        smile_y = center[1] + 20
        draw.arc(
            [(center[0] - 30, smile_y - 15), (center[0] + 30, smile_y + 15)],
            start=0,
            end=180,
            fill='#1f2937',
            width=3
        )
        
        # Professional label at bottom
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except Exception:
            font = ImageFont.load_default()
        
        label = "REPORTER"
        bbox = draw.textbbox((0, 0), label, font=font)
        text_width = bbox[2] - bbox[0]
        text_x = center[0] - text_width // 2
        text_y = center[1] + radius - 10
        
        # Text background
        draw.rectangle(
            [(text_x - 5, text_y - 3), (text_x + text_width + 5, text_y + (bbox[3] - bbox[1]) + 3)],
            fill='#1e40af',
            outline='#ffffff',
            width=1
        )
        draw.text((text_x, text_y), label, fill='#ffffff', font=font)
        
        img.save(output_path, 'PNG')
        return True
    except Exception as e:
        logger.error(f"create_reporter_avatar failed: {e}", exc_info=True)
        return False


def create_intro_slide(output_path: str, location: str, width: int = 1280, height: int = 720) -> bool:
    """Create a reusable intro slide image."""
    try:
        img = Image.new('RGB', (width, height), color='#1e293b')  # Dark slate background
        draw = ImageDraw.Draw(img)
        
        # Try to load a font, fallback to default if not available
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except Exception:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
        
        # Title
        title = "Local News Update"
        draw.text((width // 2, height // 2 - 60), title, fill='#ffffff', font=font_large, anchor='mm')
        
        # Location
        location_text = location
        draw.text((width // 2, height // 2 + 20), location_text, fill='#60a5fa', font=font_medium, anchor='mm')
        
        # Time
        time_text = datetime.now().strftime('%B %d, %Y - %I:%M %p')
        draw.text((width // 2, height // 2 + 70), time_text, fill='#94a3b8', font=font_medium, anchor='mm')
        
        img.save(output_path, 'PNG')
        return True
    except Exception as e:
        logger.error(f"create_intro_slide failed: {e}", exc_info=True)
        return False


def create_ending_slide(output_path: str, width: int = 1280, height: int = 720) -> bool:
    """Create a reusable ending slide image."""
    try:
        img = Image.new('RGB', (width, height), color='#1e293b')  # Dark slate background
        draw = ImageDraw.Draw(img)
        
        # Try to load a font, fallback to default if not available
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except Exception:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
        
        # Ending message
        message = "Thank You For Watching"
        draw.text((width // 2, height // 2 - 40), message, fill='#ffffff', font=font_large, anchor='mm')
        
        # Stay tuned
        stay_tuned = "Stay Tuned For More Updates"
        draw.text((width // 2, height // 2 + 40), stay_tuned, fill='#94a3b8', font=font_medium, anchor='mm')
        
        img.save(output_path, 'PNG')
        return True
    except Exception as e:
        logger.error(f"create_ending_slide failed: {e}", exc_info=True)
        return False


def _get_recent_articles(limit: int = 10, hours: int = 48) -> List[Article]:
    """Get recent articles from the last N hours."""
    session = SessionLocal()
    try:
        cutoff = get_local_now() - timedelta(hours=hours)
        articles = (
            session.query(Article)
            .filter(
                Article.is_published == True,
                Article.ai_body.isnot(None),
                Article.fetched_at >= cutoff
            )
            .order_by(Article.fetched_at.desc())
            .limit(limit)
            .all()
        )
        return articles
    finally:
        session.close()


def generate_broadcast_script(
    articles: List[Article],
    weather_report: Optional[str],
    location: str,
    *,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout_s: int = 1800
) -> Optional[str]:
    """Generate a broadcast script using Ollama. Returns full script for transcript."""
    if not articles:
        return None
    
    # Build article summaries for the prompt
    article_texts = []
    for i, art in enumerate(articles[:15], 1):  # Limit to 15 articles
        title = art.ai_title or art.source_title or "Untitled"
        body = (art.ai_body or art.raw_content or "")[:500]  # Truncate for prompt
        article_texts.append(f"{i}. {title}\n{body}")
    
    articles_summary = "\n\n".join(article_texts)
    
    weather_text = weather_report or "Weather information unavailable."
    
    system_prompt = (
        "You are a professional news broadcaster. Create a natural, engaging news broadcast script "
        "that covers the provided articles and includes a weather segment. "
        "Write in a conversational yet authoritative tone suitable for a video broadcast. "
        "Include smooth transitions between stories. Keep each story concise but informative. "
        "End with a weather forecast segment."
    )
    
    user_prompt = (
        f"Location: {location}\n\n"
        f"News Articles ({len(articles)} stories):\n{articles_summary}\n\n"
        f"Weather Forecast:\n{weather_text}\n\n"
        "Create a complete broadcast script that covers these stories and the weather. "
        "Format it as a natural broadcast script that flows well when spoken aloud."
    )
    
    payload = {
        "model": (model or DEFAULT_OLLAMA_MODEL),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {"temperature": 0.7},
    }
    
    try:
        data = _post_ollama("/api/chat", payload, base_url=base_url, timeout_s=timeout_s)
        message = data.get("message", {})
        script = message.get("content", "")
        if script:
            return script.strip()
    except Exception as e:
        logger.error(f"generate_broadcast_script failed: {e}", exc_info=True)
        return None
    return None


def generate_article_script(
    article: Article,
    location: str,
    *,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout_s: int = 300
) -> Optional[str]:
    """Generate a short broadcast script segment for a single article with a funny reporter name."""
    title = article.ai_title or article.source_title or "Untitled"
    body = (article.ai_body or article.raw_content or "")[:800]  # Limit body length
    
    system_prompt = (
        "You are a professional news broadcaster. Create a concise, engaging news segment "
        "for this article. Write 2-4 sentences that summarize the key points in a natural, "
        "conversational tone suitable for broadcast. IMPORTANT: At the beginning of the segment, "
        "create a funny, creative reporter name (like 'Chuck Reportington', 'Sally Newsworthy', "
        "'Bob Broadcast', etc.) and introduce the story as if that reporter is reading it. "
        "Format it as: '[Reporter Name] reporting: [story content]'"
    )
    
    user_prompt = (
        f"Location: {location}\n\n"
        f"Article Title: {title}\n\n"
        f"Article Content:\n{body}\n\n"
        "Write a brief news segment (2-4 sentences) covering this story. Start with a funny "
        "reporter name introduction, like '[Funny Reporter Name] reporting: [story content]'"
    )
    
    payload = {
        "model": (model or DEFAULT_OLLAMA_MODEL),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {"temperature": 0.7},
    }
    
    try:
        data = _post_ollama("/api/chat", payload, base_url=base_url, timeout_s=timeout_s)
        message = data.get("message", {})
        script = message.get("content", "")
        if script:
            return script.strip()
    except Exception as e:
        logger.warning(f"generate_article_script failed for article {article.id}: {e}")
        return None
    return None


def create_article_placeholder_image(article: Article, output_path: str, width: int = 1280, height: int = 720) -> bool:
    """Create a placeholder image for an article when download fails."""
    try:
        # Create blank image
        img = Image.new('RGB', (width, height), color='#334155')  # Dark slate-gray background
        draw = ImageDraw.Draw(img)
        
        # Try to load a font, fallback to default if not available
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        except Exception:
            font_title = ImageFont.load_default()
            font_label = ImageFont.load_default()
        
        # Get article title
        title = article.ai_title or article.source_title or "News Story"
        
        # Helper function to wrap text
        def wrap_text(text: str, font, max_width: int) -> List[str]:
            """Wrap text to fit within max_width."""
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                # Get text size
                bbox = draw.textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]
                
                if text_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        current_line.append(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            return lines if lines else [text]
        
        # Wrap title text
        max_title_width = width - 160  # Leave 80px margins
        title_lines = wrap_text(title, font_title, max_title_width)
        
        # Limit to 3 lines max
        if len(title_lines) > 3:
            title_lines = title_lines[:3]
            title_lines[-1] = title_lines[-1][:80] + "..." if len(title_lines[-1]) > 80 else title_lines[-1]
        
        # Calculate title position (centered)
        line_heights = []
        for line in title_lines:
            bbox = draw.textbbox((0, 0), line, font=font_title)
            line_heights.append(bbox[3] - bbox[1])
        
        total_title_height = sum(line_heights) + (len(title_lines) - 1) * 15  # 15px spacing
        title_start_y = (height - total_title_height) // 2 - 40
        
        # Draw title lines
        y_offset = title_start_y
        for i, line in enumerate(title_lines):
            bbox = draw.textbbox((0, 0), line, font=font_title)
            text_width = bbox[2] - bbox[0]
            x_offset = (width - text_width) // 2
            draw.text((x_offset, y_offset), line, fill='#ffffff', font=font_title)
            y_offset += line_heights[i] + 15
        
        # Draw "News Story" label at bottom
        label = "News Story"
        bbox = draw.textbbox((0, 0), label, font=font_label)
        label_width = bbox[2] - bbox[0]
        label_x = (width - label_width) // 2
        label_y = height - 100
        draw.text((label_x, label_y), label, fill='#94a3b8', font=font_label)
        
        img.save(output_path, 'PNG')
        logger.info(f"Created placeholder image for article {article.id}: {output_path}")
        return True
    except Exception as e:
        logger.error(f"create_article_placeholder_image failed for article {article.id}: {e}", exc_info=True)
        return False


def download_article_images(articles: List[Article], images_dir: str) -> Dict[int, str]:
    """Download article images and return mapping of article_id -> local_path.
    Creates placeholder images when download fails."""
    image_paths = {}
    
    for article in articles:
        local_path = os.path.join(images_dir, f"article_{article.id}.jpg")
        placeholder_path = os.path.join(images_dir, f"article_{article.id}_placeholder.png")
        
        # Skip if already downloaded or placeholder exists
        if os.path.exists(local_path):
            image_paths[article.id] = local_path
            continue
        
        if os.path.exists(placeholder_path):
            image_paths[article.id] = placeholder_path
            continue
        
        # Try to download if we have an image URL
        if article.image_url:
            try:
                resp = requests.get(article.image_url, timeout=10, stream=True, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                resp.raise_for_status()
                
                # Save image
                with open(local_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Verify it's a valid image
                try:
                    img = Image.open(local_path)
                    img.verify()
                    image_paths[article.id] = local_path
                    logger.info(f"Successfully downloaded image for article {article.id}")
                    continue
                except Exception:
                    # Invalid image, remove it
                    try:
                        os.remove(local_path)
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Failed to download image for article {article.id}: {e}")
        
        # Download failed or no image URL - create placeholder
        logger.info(f"Creating placeholder image for article {article.id}")
        if create_article_placeholder_image(article, placeholder_path):
            image_paths[article.id] = placeholder_path
        else:
            logger.error(f"Failed to create placeholder for article {article.id}")
    
    return image_paths


def fetch_base_map_image(lat: float, lon: float, zoom: int = 8) -> Optional[Image.Image]:
    """Fetch base map tiles from OpenStreetMap.
    Returns PIL Image object or None if failed.
    """
    try:
        # Calculate tile coordinates
        def lat_lon_to_tile(lat, lon, zoom):
            lat_rad = math.radians(lat)
            n = 2.0 ** zoom
            x_tile = int((lon + 180.0) / 360.0 * n)
            y_tile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
            return x_tile, y_tile

        center_x, center_y = lat_lon_to_tile(lat, lon, zoom)

        # Fetch 3x3 grid
        tile_size = 256
        grid_size = 3
        composite = Image.new('RGB', (tile_size * grid_size, tile_size * grid_size), (200, 200, 200))

        # OpenStreetMap tile server
        # Using tile.openstreetmap.org as fallback
        tiles_fetched = 0
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                tile_x = center_x + dx
                tile_y = center_y + dy

                # OSM tile URL
                tile_url = f"https://tile.openstreetmap.org/{zoom}/{tile_x}/{tile_y}.png"

                try:
                    tile_resp = requests.get(tile_url, timeout=5, headers={
                        'User-Agent': 'News-AI-Broadcast/1.0'
                    })
                    tile_resp.raise_for_status()

                    tile_img = Image.open(io.BytesIO(tile_resp.content))
                    paste_x = (dx + 1) * tile_size
                    paste_y = (dy + 1) * tile_size
                    composite.paste(tile_img, (paste_x, paste_y))
                    tiles_fetched += 1

                except Exception as e:
                    logger.debug(f"Failed to fetch base map tile ({tile_x}, {tile_y}): {e}")

        if tiles_fetched > 0:
            logger.info(f"Fetched {tiles_fetched}/{grid_size*grid_size} base map tiles")
            return composite
        else:
            logger.warning("No base map tiles fetched")
            return None

    except Exception as e:
        logger.warning(f"Failed to fetch base map: {e}")
        return None


def fetch_weather_radar_image(lat: float, lon: float, zoom: int = 8, width: int = 800, height: int = 600) -> Optional[bytes]:
    """Fetch weather radar/precipitation map from OpenWeatherMap.
    Returns composite image bytes (PNG) or None if failed.
    Uses OpenWeatherMap Weather Map API: https://openweathermap.org/api/weathermaps
    """
    try:
        # Get API key from environment
        api_key = os.environ.get('OPENWEATHERMAP_API_KEY')
        if not api_key:
            logger.warning("OPENWEATHERMAP_API_KEY not set, skipping radar fetch")
            return None

        # Calculate tile coordinates for center point
        # OpenWeatherMap uses standard slippy map tilenames
        def lat_lon_to_tile(lat, lon, zoom):
            lat_rad = math.radians(lat)
            n = 2.0 ** zoom
            x_tile = int((lon + 180.0) / 360.0 * n)
            y_tile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
            return x_tile, y_tile

        center_x, center_y = lat_lon_to_tile(lat, lon, zoom)

        # Fetch a 3x3 grid of tiles centered on the location
        # This gives us a nice area view
        tile_size = 256  # OpenWeatherMap tiles are 256x256
        grid_size = 3
        composite_width = tile_size * grid_size
        composite_height = tile_size * grid_size

        # Create composite image
        composite = Image.new('RGBA', (composite_width, composite_height), (0, 0, 0, 0))

        # OpenWeatherMap precipitation layer
        layer = "precipitation_new"

        logger.info(f"Fetching {grid_size}x{grid_size} radar tiles for location ({lat:.2f}, {lon:.2f}) at zoom {zoom}")

        # Fetch tiles
        tiles_fetched = 0
        for dy in range(-1, 2):  # -1, 0, 1
            for dx in range(-1, 2):  # -1, 0, 1
                tile_x = center_x + dx
                tile_y = center_y + dy

                # Tile URL format: https://tile.openweathermap.org/map/{layer}/{z}/{x}/{y}.png?appid={API key}
                tile_url = f"https://tile.openweathermap.org/map/{layer}/{zoom}/{tile_x}/{tile_y}.png?appid={api_key}"

                try:
                    tile_resp = requests.get(tile_url, timeout=5)
                    tile_resp.raise_for_status()

                    # Load tile image
                    tile_img = Image.open(io.BytesIO(tile_resp.content))

                    # Paste into composite
                    paste_x = (dx + 1) * tile_size
                    paste_y = (dy + 1) * tile_size
                    composite.paste(tile_img, (paste_x, paste_y))
                    tiles_fetched += 1

                except Exception as e:
                    logger.debug(f"Failed to fetch tile ({tile_x}, {tile_y}): {e}")
                    # Continue with other tiles

        if tiles_fetched == 0:
            logger.warning("No radar tiles fetched successfully")
            return None

        logger.info(f"Fetched {tiles_fetched}/{grid_size*grid_size} radar tiles successfully")

        # Fetch base map
        logger.info("Fetching base map tiles...")
        base_map = fetch_base_map_image(lat, lon, zoom)

        # Composite radar over base map
        if base_map:
            # Convert base map to RGBA
            base_map = base_map.convert('RGBA')
            # Composite radar layer on top
            final_image = Image.alpha_composite(base_map, composite)
            logger.info("Composited radar over base map")
        else:
            # Use just the radar overlay
            final_image = composite
            logger.info("Using radar overlay only (no base map)")

        # Resize to requested dimensions
        final_image = final_image.resize((width, height), Image.LANCZOS)

        # Convert to PNG bytes
        output = io.BytesIO()
        final_image.save(output, format='PNG')
        return output.getvalue()

    except Exception as e:
        logger.warning(f"Failed to fetch weather radar: {e}")
        return None


def create_radar_weather_card(weather_report: Optional[WeatherReport], output_path: str, width: int = 1280, height: int = 720) -> bool:
    """Create a composite weather card with radar/map visualization and 5-day forecast.
    This creates a visual weather card similar to TV weather reports."""
    try:
        # Create image with gradient background
        img = Image.new('RGB', (width, height), color='#0F172A')
        draw = ImageDraw.Draw(img)

        # Draw gradient background
        for y in range(height):
            ratio = y / height
            r = int(15 + (30 - 15) * ratio)
            g = int(23 + (58 - 23) * ratio)
            b = int(42 + (95 - 42) * ratio)
            color = f'#{r:02x}{g:02x}{b:02x}'
            draw.line([(0, y), (width, y)], fill=color)

        # Load fonts
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except Exception:
            font_title = ImageFont.load_default()
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_tiny = ImageFont.load_default()

        # Header
        header_height = 80
        draw.rectangle([(0, 0), (width, header_height)], fill='#1E3A8A')
        draw.text((width // 2, header_height // 2), "LOCAL WEATHER MAP", fill='#FFFFFF', font=font_title, anchor='mm')

        # Radar/Map section (top half)
        radar_y_start = header_height + 20
        radar_height = 280
        radar_left = 60
        radar_right = width - 60

        # Draw radar placeholder with border
        draw.rectangle(
            [(radar_left, radar_y_start), (radar_right, radar_y_start + radar_height)],
            fill='#1E293B',
            outline='#3B82F6',
            width=3
        )

        # Attempt to fetch actual radar (if available)
        radar_fetched = False
        if weather_report and weather_report.latitude and weather_report.longitude:
            try:
                lat = weather_report.latitude
                lon = weather_report.longitude

                # Try to fetch radar image
                radar_bytes = fetch_weather_radar_image(lat, lon, zoom=8, width=radar_right-radar_left, height=radar_height)

                if radar_bytes:
                    # Load and paste radar image
                    radar_img = Image.open(io.BytesIO(radar_bytes))
                    radar_img = radar_img.resize((radar_right - radar_left, radar_height))
                    img.paste(radar_img, (radar_left, radar_y_start))
                    radar_fetched = True
                    logger.info("Weather radar image fetched and embedded")
            except Exception as e:
                logger.warning(f"Could not embed radar image: {e}")

        # If radar not fetched, show a nice placeholder
        if not radar_fetched:
            # Create a stylized map placeholder
            radar_center_x = (radar_left + radar_right) // 2
            radar_center_y = radar_y_start + (radar_height // 2)

            # Draw concentric circles to simulate radar
            for i in range(4):
                radius = 30 + (i * 25)
                circle_color = f'#{40 + i*15:02x}{60 + i*20:02x}{140 + i*10:02x}'
                draw.ellipse(
                    [(radar_center_x - radius, radar_center_y - radius),
                     (radar_center_x + radius, radar_center_y + radius)],
                    outline=circle_color,
                    width=2
                )

            # Center marker
            marker_size = 15
            draw.ellipse(
                [(radar_center_x - marker_size, radar_center_y - marker_size),
                 (radar_center_x + marker_size, radar_center_y + marker_size)],
                fill='#EF4444',
                outline='#FFFFFF',
                width=2
            )

            # Location text
            location_text = weather_report.location if weather_report else "Your Location"
            draw.text((radar_center_x, radar_y_start + radar_height - 30), location_text,
                     fill='#60A5FA', font=font_medium, anchor='mm')

            # Radar label
            draw.text((radar_center_x, radar_y_start + 30), "PRECIPITATION MAP",
                     fill='#94A3B8', font=font_small, anchor='mm')

        # 5-Day Forecast section (bottom)
        forecast_y_start = radar_y_start + radar_height + 40

        # Section title
        draw.text((width // 2, forecast_y_start), "5-DAY FORECAST",
                 fill='#60A5FA', font=font_large, anchor='mm')
        forecast_y_start += 60

        # Parse forecast data
        if weather_report and weather_report.forecast_json:
            try:
                forecast = json.loads(weather_report.forecast_json)
                daily = forecast.get('daily', {})

                times = daily.get('time', [])
                max_temps = daily.get('temperature_2m_max', [])
                min_temps = daily.get('temperature_2m_min', [])
                weather_codes = daily.get('weathercode', [])

                num_days = min(5, len(times) if times else 0)

                if num_days > 0:
                    # Calculate card dimensions
                    card_spacing = 20
                    total_card_width = width - 120  # Margins
                    card_width = (total_card_width - (card_spacing * (num_days - 1))) // num_days
                    card_height = 180

                    # Draw forecast cards
                    for day_idx in range(num_days):
                        card_x = 60 + (day_idx * (card_width + card_spacing))
                        card_center_x = card_x + (card_width // 2)

                        # Parse date
                        date_str = times[day_idx] if day_idx < len(times) else ""
                        try:
                            from datetime import datetime as dt
                            date_obj = dt.fromisoformat(date_str.replace('Z', '+00:00'))
                            day_name = date_obj.strftime('%a').upper()
                            day_num = date_obj.strftime('%d')
                        except Exception:
                            day_name = f"DAY {day_idx+1}"
                            day_num = ""

                        # Draw card
                        draw.rounded_rectangle(
                            [(card_x, forecast_y_start), (card_x + card_width, forecast_y_start + card_height)],
                            radius=15,
                            fill='#1E293B',
                            outline='#475569',
                            width=3
                        )

                        # Day name and date
                        draw.text((card_center_x, forecast_y_start + 25), day_name,
                                 fill='#94A3B8', font=font_medium, anchor='mm')
                        if day_num:
                            draw.text((card_center_x, forecast_y_start + 55), day_num,
                                     fill='#CBD5E1', font=font_small, anchor='mm')

                        # Weather icon - use helper function that properly handles emoji fonts
                        weather_code = weather_codes[day_idx] if day_idx < len(weather_codes) else 0
                        _draw_weather_icon(draw, weather_code, card_center_x, forecast_y_start + 95, size=40)

                        # Temperatures
                        max_temp = max_temps[day_idx] if day_idx < len(max_temps) and max_temps[day_idx] is not None else None
                        min_temp = min_temps[day_idx] if day_idx < len(min_temps) and min_temps[day_idx] is not None else None

                        if max_temp is not None and min_temp is not None:
                            # High temp
                            draw.text((card_center_x, forecast_y_start + 135), f"{int(max_temp)}°",
                                     fill='#F87171', font=font_medium, anchor='mm')
                            # Low temp
                            draw.text((card_center_x, forecast_y_start + 162), f"{int(min_temp)}°",
                                     fill='#60A5FA', font=font_small, anchor='mm')

            except Exception as e:
                logger.warning(f"Failed to render 5-day forecast on radar card: {e}")
                draw.text((width // 2, forecast_y_start + 80), "Forecast data unavailable",
                         fill='#94A3B8', font=font_medium, anchor='mm')
        else:
            draw.text((width // 2, forecast_y_start + 80), "No forecast data available",
                     fill='#94A3B8', font=font_medium, anchor='mm')

        # Save image
        img.save(output_path, 'PNG')
        logger.info(f"Radar weather card created: {output_path}")
        return True

    except Exception as e:
        logger.error(f"create_radar_weather_card failed: {e}", exc_info=True)
        return False


def _get_weather_icon_and_color(weather_code: int) -> Tuple[str, str, str]:
    """Map WMO weather code to icon symbol, color, and description.
    Returns (unicode_symbol, color_hex, description).
    WMO codes: https://open-meteo.com/en/docs
    """
    # Clear skies
    if weather_code == 0:
        return "☀️", "#FDB813", "Clear"
    # Mainly clear
    elif weather_code in [1, 2]:
        return "🌤️", "#FDB813", "Mostly Clear"
    # Partly cloudy
    elif weather_code == 3:
        return "⛅", "#94A3B8", "Partly Cloudy"
    # Overcast/Foggy
    elif weather_code in [45, 48]:
        return "🌫️", "#64748B", "Foggy"
    # Drizzle
    elif weather_code in [51, 53, 55, 56, 57]:
        return "🌦️", "#60A5FA", "Drizzle"
    # Rain
    elif weather_code in [61, 63, 65, 66, 67, 80, 81, 82]:
        return "🌧️", "#3B82F6", "Rain"
    # Snow
    elif weather_code in [71, 73, 75, 77, 85, 86]:
        return "❄️", "#93C5FD", "Snow"
    # Thunderstorm
    elif weather_code in [95, 96, 99]:
        return "⛈️", "#7C3AED", "Thunderstorm"
    # Default
    else:
        return "🌡️", "#94A3B8", "Variable"


def _draw_weather_icon(draw: ImageDraw.ImageDraw, weather_code: int, center_x: int, center_y: int, size: int = 60):
    """Draw a simple geometric weather icon based on WMO weather code.

    Uses basic shapes instead of emojis to ensure reliable rendering.
    """
    _, color_hex, condition = _get_weather_icon_and_color(weather_code)

    # Convert hex color to RGB tuple
    color = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

    # Draw icon based on weather code
    if weather_code == 0:  # Clear
        # Draw sun (circle with rays)
        sun_radius = size // 2
        draw.ellipse(
            [(center_x - sun_radius, center_y - sun_radius),
             (center_x + sun_radius, center_y + sun_radius)],
            fill='#FDB813', outline='#F59E0B', width=3
        )
        # Sun rays
        ray_length = size // 3
        for angle in range(0, 360, 45):
            import math
            rad = math.radians(angle)
            x1 = center_x + int((sun_radius + 5) * math.cos(rad))
            y1 = center_y + int((sun_radius + 5) * math.sin(rad))
            x2 = center_x + int((sun_radius + ray_length) * math.cos(rad))
            y2 = center_y + int((sun_radius + ray_length) * math.sin(rad))
            draw.line([(x1, y1), (x2, y2)], fill='#FDB813', width=3)

    elif weather_code in [1, 2]:  # Mostly clear
        # Sun with small cloud
        sun_r = size // 3
        draw.ellipse(
            [(center_x - sun_r - 10, center_y - sun_r),
             (center_x + sun_r - 10, center_y + sun_r)],
            fill='#FDB813', outline='#F59E0B', width=2
        )
        # Small cloud
        cloud_x = center_x + 10
        draw.ellipse([(cloud_x - 15, center_y - 10), (cloud_x + 15, center_y + 20)], fill='#E2E8F0')
        draw.ellipse([(cloud_x - 5, center_y - 15), (cloud_x + 20, center_y + 15)], fill='#E2E8F0')

    elif weather_code == 3:  # Partly cloudy
        # Cloud
        draw.ellipse([(center_x - 25, center_y - 10), (center_x + 5, center_y + 20)], fill='#CBD5E1')
        draw.ellipse([(center_x - 10, center_y - 15), (center_x + 25, center_y + 20)], fill='#CBD5E1')
        draw.ellipse([(center_x, center_y - 10), (center_x + 20, center_y + 15)], fill='#CBD5E1')

    elif weather_code in [45, 48]:  # Foggy
        # Horizontal lines for fog
        for i in range(4):
            y = center_y - 20 + (i * 12)
            draw.line([(center_x - 25, y), (center_x + 25, y)], fill='#94A3B8', width=4)

    elif weather_code in [51, 53, 55, 56, 57]:  # Drizzle
        # Cloud with light rain
        draw.ellipse([(center_x - 20, center_y - 20), (center_x + 20, center_y + 5)], fill='#94A3B8')
        # Light rain drops
        for i in range(3):
            x = center_x - 15 + (i * 15)
            draw.line([(x, center_y + 8), (x, center_y + 20)], fill='#60A5FA', width=2)

    elif weather_code in [61, 63, 65, 66, 67, 80, 81, 82]:  # Rain
        # Cloud with rain
        draw.ellipse([(center_x - 25, center_y - 20), (center_x + 5, center_y + 5)], fill='#64748B')
        draw.ellipse([(center_x - 10, center_y - 25), (center_x + 25, center_y + 5)], fill='#64748B')
        # Rain drops
        for i in range(4):
            x = center_x - 20 + (i * 13)
            draw.line([(x, center_y + 8), (x, center_y + 25)], fill='#3B82F6', width=3)

    elif weather_code in [71, 73, 75, 77, 85, 86]:  # Snow
        # Cloud with snowflakes
        draw.ellipse([(center_x - 20, center_y - 20), (center_x + 20, center_y + 5)], fill='#94A3B8')
        # Snowflakes (asterisks)
        for i in range(3):
            x = center_x - 15 + (i * 15)
            y = center_y + 15
            # Simple asterisk shape
            draw.line([(x, y - 5), (x, y + 5)], fill='#FFFFFF', width=2)
            draw.line([(x - 4, y), (x + 4, y)], fill='#FFFFFF', width=2)
            draw.line([(x - 3, y - 3), (x + 3, y + 3)], fill='#FFFFFF', width=2)
            draw.line([(x - 3, y + 3), (x + 3, y - 3)], fill='#FFFFFF', width=2)

    elif weather_code in [95, 96, 99]:  # Thunderstorm
        # Dark cloud with lightning
        draw.ellipse([(center_x - 25, center_y - 20), (center_x + 5, center_y + 5)], fill='#475569')
        draw.ellipse([(center_x - 10, center_y - 25), (center_x + 25, center_y + 5)], fill='#475569')
        # Lightning bolt
        lightning = [
            (center_x, center_y + 5),
            (center_x - 5, center_y + 15),
            (center_x, center_y + 15),
            (center_x - 8, center_y + 28)
        ]
        draw.line(lightning, fill='#FCD34D', width=4)

    else:  # Default
        # Simple thermometer
        draw.rectangle(
            [(center_x - 8, center_y - 20), (center_x + 8, center_y + 10)],
            fill='#E2E8F0', outline='#94A3B8', width=2
        )
        draw.ellipse(
            [(center_x - 12, center_y + 5), (center_x + 12, center_y + 25)],
            fill='#EF4444', outline='#DC2626', width=2
        )


def create_weather_slide(weather_report: Optional[WeatherReport], output_path: str, width: int = 1280, height: int = 720) -> bool:
    """Create a professional weather forecast slide with icons and proper styling."""
    try:
        # Create gradient background (dark blue to lighter blue)
        img = Image.new('RGB', (width, height), color='#0F172A')  # Very dark slate
        draw = ImageDraw.Draw(img)

        # Draw gradient background
        for y in range(height):
            # Gradient from dark slate to medium blue
            ratio = y / height
            r = int(15 + (30 - 15) * ratio)
            g = int(23 + (58 - 23) * ratio)
            b = int(42 + (95 - 42) * ratio)
            color = f'#{r:02x}{g:02x}{b:02x}'
            draw.line([(0, y), (width, y)], fill=color)

        # Try to load fonts
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            font_regular = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except Exception:
            font_title = ImageFont.load_default()
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_regular = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_tiny = ImageFont.load_default()
        
        # Draw header bar
        header_height = 100
        draw.rectangle([(0, 0), (width, header_height)], fill='#1E3A8A')  # Deep blue header

        # Title
        title = "WEATHER FORECAST"
        draw.text((width // 2, header_height // 2), title, fill='#FFFFFF', font=font_title, anchor='mm')

        # Current weather section
        current_y_start = header_height + 40

        if weather_report and weather_report.forecast_json:
            try:
                forecast = json.loads(weather_report.forecast_json)
                current = forecast.get('current_weather', {})
                daily = forecast.get('daily', {})

                # Draw current weather (large display)
                if current:
                    temp = current.get('temperature')
                    weather_code = current.get('weathercode', 0)
                    wind_speed = current.get('windspeed', 0)

                    # Current temperature (large)
                    if temp is not None:
                        temp_text = f"{int(temp)}°"
                        draw.text((220, current_y_start + 80), temp_text, fill='#FFFFFF', font=font_title, anchor='mm')

                        # Weather icon for current conditions - use geometric shapes
                        _, icon_color, condition = _get_weather_icon_and_color(weather_code)
                        _draw_weather_icon(draw, weather_code, 220, current_y_start + 180, size=80)

                        # Condition text
                        draw.text((220, current_y_start + 240), condition, fill='#E2E8F0', font=font_regular, anchor='mm')

                        # Wind speed
                        if wind_speed:
                            wind_text = f"Wind: {int(wind_speed)} mph"
                            draw.text((220, current_y_start + 280), wind_text, fill='#CBD5E1', font=font_small, anchor='mm')

                # Draw summary text (right side)
                if weather_report.ai_report:
                    summary_x = 500
                    summary_y = current_y_start + 20
                    summary_width = width - summary_x - 40

                    # Summary title
                    draw.text((summary_x, summary_y), "TODAY'S FORECAST", fill='#60A5FA', font=font_medium, anchor='lm')
                    summary_y += 50

                    # Summary text (first 3 sentences)
                    summary_text = weather_report.ai_report.strip()
                    sentences = summary_text.split('.')[:3]
                    summary_short = '. '.join(s.strip() for s in sentences if s.strip())
                    if summary_short and not summary_short.endswith('.'):
                        summary_short += '.'

                    # Word wrap summary
                    words = summary_short.split()
                    lines = []
                    current_line = []

                    for word in words:
                        test_line = ' '.join(current_line + [word])
                        bbox = draw.textbbox((0, 0), test_line, font=font_regular)
                        text_width = bbox[2] - bbox[0]

                        if text_width <= summary_width:
                            current_line.append(word)
                        else:
                            if current_line:
                                lines.append(' '.join(current_line))
                                current_line = [word]
                            else:
                                current_line.append(word)

                    if current_line:
                        lines.append(' '.join(current_line))

                    # Draw summary lines (max 6 lines)
                    for i, line in enumerate(lines[:6]):
                        draw.text((summary_x, summary_y), line, fill='#E2E8F0', font=font_regular, anchor='lm')
                        summary_y += 35

                # 5-day forecast section
                forecast_y_start = current_y_start + 320

                # Draw separator line
                draw.line([(60, forecast_y_start), (width - 60, forecast_y_start)], fill='#475569', width=2)

                forecast_y_start += 30

                # 5-day forecast header
                draw.text((width // 2, forecast_y_start), "5-DAY FORECAST", fill='#60A5FA', font=font_medium, anchor='mm')
                forecast_y_start += 50

                # Get 5-day forecast data
                if daily:
                    times = daily.get('time', [])
                    max_temps = daily.get('temperature_2m_max', [])
                    min_temps = daily.get('temperature_2m_min', [])
                    weather_codes = daily.get('weathercode', [])

                    # Limit to 5 days
                    num_days = min(5, len(times) if times else 0)

                    if num_days > 0:
                        # Calculate layout for 5 days
                        day_width = (width - 200) // num_days
                        card_y_start = forecast_y_start

                        # Draw each day as a card
                        for day_idx in range(num_days):
                            day_x = 100 + (day_idx * day_width)
                            day_center_x = day_x + (day_width // 2)

                            # Parse date
                            date_str = times[day_idx] if day_idx < len(times) else ""
                            try:
                                from datetime import datetime as dt
                                date_obj = dt.fromisoformat(date_str.replace('Z', '+00:00'))
                                day_name = date_obj.strftime('%a')  # Mon, Tue, etc.
                                day_num = date_obj.strftime('%d')  # Day number
                            except Exception:
                                day_name = f"Day {day_idx+1}"
                                day_num = ""

                            # Draw day card background
                            card_left = day_x + 5
                            card_right = day_x + day_width - 5
                            card_top = card_y_start
                            card_bottom = card_y_start + 200
                            draw.rounded_rectangle(
                                [(card_left, card_top), (card_right, card_bottom)],
                                radius=10,
                                fill='#1E293B',
                                outline='#475569',
                                width=2
                            )

                            # Draw day name
                            draw.text((day_center_x, card_top + 20), day_name.upper(), fill='#94A3B8', font=font_small, anchor='mm')
                            draw.text((day_center_x, card_top + 45), day_num, fill='#CBD5E1', font=font_tiny, anchor='mm')

                            # Weather icon - use geometric shapes
                            weather_code = weather_codes[day_idx] if day_idx < len(weather_codes) else 0
                            _draw_weather_icon(draw, weather_code, day_center_x, card_top + 95, size=48)

                            # Temperatures
                            max_temp = max_temps[day_idx] if day_idx < len(max_temps) and max_temps[day_idx] is not None else None
                            min_temp = min_temps[day_idx] if day_idx < len(min_temps) and min_temps[day_idx] is not None else None

                            if max_temp is not None:
                                draw.text((day_center_x, card_top + 145), f"{int(max_temp)}°", fill='#F87171', font=font_medium, anchor='mm')
                            if min_temp is not None:
                                draw.text((day_center_x, card_top + 175), f"{int(min_temp)}°", fill='#60A5FA', font=font_small, anchor='mm')
            except Exception as e:
                logger.warning(f"Failed to parse forecast JSON for visual: {e}")
                # Show error message on slide
                error_msg = "Weather data temporarily unavailable"
                draw.text((width // 2, height // 2), error_msg, fill='#E2E8F0', font=font_medium, anchor='mm')
        else:
            # No weather report available
            no_data_msg = "Weather forecast not available"
            draw.text((width // 2, height // 2), no_data_msg, fill='#E2E8F0', font=font_large, anchor='mm')

        img.save(output_path, 'PNG')
        logger.info(f"Weather slide created: {output_path}")
        return True
    except Exception as e:
        logger.error(f"create_weather_slide failed: {e}", exc_info=True)
        return False


def _smart_chunk_text(text: str, max_chars: int = 1000) -> List[str]:
    """Intelligently chunk text by sentences to avoid TTS truncation.

    TTS engines often have internal character limits (1000-5000 chars).
    This function splits text at sentence boundaries to ensure complete audio.

    Args:
        text: Text to chunk
        max_chars: Maximum characters per chunk (default 1000 for safety)

    Returns:
        List of text chunks, each ending at a sentence boundary
    """
    if len(text) <= max_chars:
        return [text]

    import re
    # Split by sentence endings, keeping punctuation
    sentences = re.split(r'([.!?]+\s+)', text)

    chunks = []
    current_chunk = ""

    for i in range(0, len(sentences)):
        sentence = sentences[i]
        if not sentence.strip():
            continue

        # Would adding this sentence exceed limit?
        if current_chunk and len(current_chunk) + len(sentence) > max_chars:
            # Save current chunk and start new one
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += sentence

    # Add remaining chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    logger.info(f"Chunked text: {len(text)} chars → {len(chunks)} chunks")
    return chunks if chunks else [text]


def _generate_word_level_captions(text: str, duration: float, start_time: float = 0.0) -> List[Dict[str, Any]]:
    """Generate word-level caption entries for better sync.

    Args:
        text: The text to caption
        duration: Audio duration in seconds
        start_time: Start time offset in seconds

    Returns:
        List of caption entries with precise word-level timing
    """
    import re

    # Split into words while preserving punctuation
    words = re.findall(r'\S+', text)

    if not words:
        return []

    # Calculate average time per word
    time_per_word = duration / len(words)

    captions = []
    current_time = start_time

    # Group words into natural phrases (3-5 words each for readability)
    WORDS_PER_CAPTION = 4

    for i in range(0, len(words), WORDS_PER_CAPTION):
        phrase_words = words[i:i + WORDS_PER_CAPTION]
        phrase = ' '.join(phrase_words)
        phrase_duration = len(phrase_words) * time_per_word

        captions.append({
            'start': current_time,
            'end': current_time + phrase_duration,
            'text': phrase
        })

        current_time += phrase_duration

    return captions


def _generate_tts_with_chunking(
    client: TTSClient,
    text: str,
    voice: Optional[str],
    timeout: int,
    temp_dir: str,
    segment_name: str
) -> Optional[Tuple[bytes, float]]:
    """Generate TTS audio with PROACTIVE chunking to prevent truncation.

    IMPORTANT: Always chunks text proactively to prevent TTS truncation.
    - Chunks text into 500-char segments (safe for all TTS engines)
    - Generates audio for each chunk
    - Concatenates all chunks seamlessly
    - Guarantees 100% of text is converted to audio

    Returns: (audio_bytes, duration) or None
    """
    # PROACTIVE CHUNKING: Always chunk text over 500 chars
    # This prevents truncation instead of trying to fix it after
    SAFE_CHUNK_SIZE = 500  # Very conservative - works with all TTS engines

    if len(text) <= SAFE_CHUNK_SIZE:
        # Short text - can send directly
        logger.info(f"Generating TTS for {len(text)} chars (single chunk)")
        audio_bytes = client.synthesize_wav(text, voice=voice, timeout=timeout)

        if not audio_bytes:
            logger.error("TTS failed for short text")
            return None

        # Get duration
        temp_path = os.path.join(temp_dir, f"_{segment_name}.wav")
        with open(temp_path, 'wb') as f:
            f.write(audio_bytes)

        try:
            from moviepy.editor import AudioFileClip
            clip = AudioFileClip(temp_path)
            duration = clip.duration
            clip.close()
            logger.info(f"✓ TTS complete: {duration:.2f}s")
            return (audio_bytes, duration)
        except Exception as e:
            logger.error(f"Failed to get duration: {e}")
            return None

    # Long text - PROACTIVELY chunk it
    chunks = _smart_chunk_text(text, max_chars=SAFE_CHUNK_SIZE)
    logger.info(f"Proactive chunking: {len(text)} chars → {len(chunks)} chunks of ~{SAFE_CHUNK_SIZE} chars")

    if len(chunks) == 1 and len(text) > SAFE_CHUNK_SIZE:
        # Chunking failed (single sentence too long) - split by words
        logger.warning(f"Single sentence too long ({len(text)} chars), splitting by words")
        words = text.split()
        chunks = []
        current = ""
        for word in words:
            if current and len(current) + len(word) + 1 > SAFE_CHUNK_SIZE:
                chunks.append(current.strip())
                current = word
            else:
                current = current + " " + word if current else word
        if current:
            chunks.append(current.strip())
        logger.info(f"Word-split: {len(text)} chars → {len(chunks)} chunks")

    chunk_audio_files = []

    # Generate audio for each chunk
    for chunk_idx, chunk in enumerate(chunks):
        logger.info(f"Generating chunk {chunk_idx+1}/{len(chunks)}: {len(chunk)} chars")
        chunk_audio = client.synthesize_wav(chunk, voice=voice, timeout=timeout)

        if not chunk_audio:
            logger.error(f"Chunk {chunk_idx+1} TTS failed")
            # Clean up
            for f in chunk_audio_files:
                try:
                    os.remove(f)
                except:
                    pass
            return None

        chunk_path = os.path.join(temp_dir, f"_chunk_{segment_name}_{chunk_idx}.wav")
        with open(chunk_path, 'wb') as f:
            f.write(chunk_audio)
        chunk_audio_files.append(chunk_path)
        logger.info(f"✓ Chunk {chunk_idx+1}/{len(chunks)} complete")

    # Concatenate all chunks
    try:
        from moviepy.editor import AudioFileClip, concatenate_audioclips

        logger.info(f"Concatenating {len(chunk_audio_files)} audio chunks...")
        clips = [AudioFileClip(f) for f in chunk_audio_files]
        final_audio = concatenate_audioclips(clips)
        total_duration = final_audio.duration

        # Save concatenated audio
        concat_path = os.path.join(temp_dir, f"_concat_{segment_name}.wav")
        final_audio.write_audiofile(concat_path, codec='pcm_s16le', logger=None)

        # Clean up
        for clip in clips:
            clip.close()
        for f in chunk_audio_files:
            try:
                os.remove(f)
            except:
                pass

        # Read final audio
        with open(concat_path, 'rb') as f:
            final_bytes = f.read()

        logger.info(f"✓ Audio concatenated: {total_duration:.2f}s total ({len(chunks)} chunks)")
        return (final_bytes, total_duration)

    except Exception as e:
        logger.error(f"Failed to concatenate chunks: {e}", exc_info=True)
        # Clean up
        for f in chunk_audio_files:
            try:
                os.remove(f)
            except:
                pass
        return None


class BroadcastSegment:
    """Individual broadcast segment with aligned video, audio, and captions."""
    def __init__(self, segment_type: str, segment_id: Any, text: str, audio_path: str,
                 video_path: str, duration: float, captions: List[Dict[str, Any]]):
        self.segment_type = segment_type  # "intro", "article", "weather", "ending"
        self.segment_id = segment_id  # article index or type string
        self.text = text
        self.audio_path = audio_path
        self.video_path = video_path
        self.duration = duration
        self.captions = captions


def create_individual_segment(
    segment_type: str,
    segment_id: Any,
    text: str,
    image_path: Optional[str],
    title: Optional[str],
    temp_dir: str,
    tts_client: TTSClient,
    voice: Optional[str] = None,
    width: int = 1280,
    height: int = 720
) -> Optional[BroadcastSegment]:
    """Create a single broadcast segment with perfectly aligned video, audio, and captions.

    This function creates ONE segment at a time, ensuring perfect synchronization:
    1. Generate TTS audio and get ACTUAL duration
    2. Create video slide with EXACT duration from audio
    3. Generate word-level captions aligned to ACTUAL audio timing

    Returns:
        BroadcastSegment with all components aligned, or None if failed
    """
    try:
        logger.info(f"=" * 80)
        logger.info(f"Creating {segment_type} segment (ID: {segment_id})")
        logger.info(f"Text: {len(text)} chars")

        # Step 1: Generate TTS audio and get ACTUAL duration
        logger.info(f"Step 1/{segment_type}: Generating TTS audio...")
        audio_result = _generate_tts_with_chunking(
            client=tts_client,
            text=text,
            voice=voice,
            timeout=1800,  # 30 min per segment
            temp_dir=temp_dir,
            segment_name=f"{segment_type}_{segment_id}"
        )

        if not audio_result:
            logger.error(f"Failed to generate TTS for {segment_type} segment")
            return None

        audio_bytes, audio_duration = audio_result
        logger.info(f"✓ Audio generated: {audio_duration:.2f} seconds")

        # Save audio
        audio_path = os.path.join(temp_dir, f"{segment_type}_{segment_id}_audio.wav")
        with open(audio_path, 'wb') as f:
            f.write(audio_bytes)

        # Step 2: Create video slide with EXACT duration from audio
        logger.info(f"Step 2/{segment_type}: Creating video slide (duration: {audio_duration:.2f}s)...")

        # Helper to resize and convert image
        def prepare_image(img_path: str) -> str:
            img = Image.open(img_path)

            # Convert to RGB if needed
            if img.mode in ('P', 'RGBA', 'LA', 'PA'):
                if img.mode in ('RGBA', 'LA', 'PA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA', 'PA') else None)
                    img = background
                else:
                    img = img.convert('RGB')

            # Resize to match video dimensions
            try:
                resized = img.resize((width, height), Image.Resampling.LANCZOS)
            except AttributeError:
                resized = img.resize((width, height), Image.LANCZOS)

            # Save temporarily
            temp_path = os.path.join(temp_dir, f"{segment_type}_{segment_id}_prepared.jpg")
            resized.save(temp_path, format='JPEG', quality=95)
            return temp_path

        # Create video clip from image with exact audio duration
        if image_path and os.path.exists(image_path):
            prepared_image = prepare_image(image_path)
        else:
            # Create placeholder
            placeholder = Image.new('RGB', (width, height), color='#1e293b')
            if title:
                draw = ImageDraw.Draw(placeholder)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
                except Exception:
                    font = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), title, font=font)
                text_width = bbox[2] - bbox[0]
                draw.text(((width - text_width) // 2, height // 2), title, fill='#ffffff', font=font)
            placeholder_path = os.path.join(temp_dir, f"{segment_type}_{segment_id}_placeholder.jpg")
            placeholder.save(placeholder_path, format='JPEG', quality=95)
            prepared_image = placeholder_path

        # Create video clip with ImageClip and AudioFileClip
        from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip

        image_clip = ImageClip(prepared_image, duration=audio_duration)
        audio_clip = AudioFileClip(audio_path)

        # Combine video and audio
        video_clip = image_clip.set_audio(audio_clip)

        # Add title overlay if provided
        if title and segment_type == "article":
            # Create title overlay
            overlay_img = Image.new('RGBA', (width, 200), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay_img)

            # Semi-transparent black background
            draw.rectangle([(40, 20), (width - 40, 100)], fill=(0, 0, 0, 180))

            # Title text
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            except Exception:
                font = ImageFont.load_default()

            # Wrap title
            words = title.split()
            lines = []
            current_line = []
            for word in words:
                test = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test, font=font)
                if bbox[2] - bbox[0] < width - 120:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))

            # Draw lines
            y = 30
            for line in lines[:2]:  # Max 2 lines
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                draw.text(((width - text_width) // 2, y), line, fill=(255, 255, 255, 255), font=font)
                y += 35

            overlay_path = os.path.join(temp_dir, f"{segment_type}_{segment_id}_overlay.png")
            overlay_img.save(overlay_path, 'PNG')

            # Add overlay to video
            overlay_clip = ImageClip(overlay_path, duration=audio_duration).set_position(('center', 'top'))
            video_clip = CompositeVideoClip([video_clip, overlay_clip])

        # Write video segment
        video_path = os.path.join(temp_dir, f"{segment_type}_{segment_id}_video.mp4")
        video_clip.write_videofile(
            video_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            verbose=False,
            logger=None
        )

        # Cleanup clips
        video_clip.close()
        audio_clip.close()
        image_clip.close()

        logger.info(f"✓ Video created: {video_path}")

        # Step 3: Generate word-level captions aligned to audio timing
        logger.info(f"Step 3/{segment_type}: Generating word-level captions...")
        captions = _generate_word_level_captions(text, audio_duration, start_time=0.0)
        logger.info(f"✓ Generated {len(captions)} caption entries")

        # Create and return segment
        segment = BroadcastSegment(
            segment_type=segment_type,
            segment_id=segment_id,
            text=text,
            audio_path=audio_path,
            video_path=video_path,
            duration=audio_duration,
            captions=captions
        )

        logger.info(f"✓ {segment_type} segment complete: {audio_duration:.2f}s")
        logger.info(f"=" * 80)
        return segment

    except Exception as e:
        logger.error(f"Failed to create {segment_type} segment: {e}", exc_info=True)
        return None


def generate_broadcast_audio_segments(
    articles: List[Article],
    weather_report: Optional[str],
    location: str,
    *,
    tts_base_url: Optional[str] = None,
    voice: Optional[str] = None,
    speed: float = 1.0,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    output_path: str,
    temp_dir: str
) -> Optional[Tuple[List[Tuple], List[str], float]]:
    """Generate TTS audio for broadcast segments (intro, articles, weather, ending).

    INTELLIGENT AUTO-CHUNKING:
    - Each segment is first sent to TTS as COMPLETE, FULL TEXT
    - If audio is detected as truncated (< 70% expected duration), automatically:
      1. Chunks text into ~1000 char segments at sentence boundaries
      2. Generates audio for each chunk
      3. Concatenates all chunk audio files
      4. Re-validates total duration
    - This ensures 100% of text is converted to audio, guaranteed!

    The "segments" refer to logical broadcast sections (intro, articles, weather, ending).
    This allows us to:
    1. Track timing for each segment (for video sync)
    2. Validate and auto-fix truncated audio
    3. Ensure complete audio for the entire transcript

    Returns: (list of (segment_id, duration) tuples, list of scripts, total_duration) or None"""
    if not articles:
        logger.warning("No articles provided for audio generation")
        return None
    
    try:
        # ==========================================================================
        # CRITICAL: NO TEXT CHUNKING OR TRUNCATION HAPPENS IN THIS FUNCTION
        # ==========================================================================
        # Each segment (intro, article, weather, ending) sends COMPLETE text to TTS
        # in a SINGLE request. No text splitting, chunking, or truncation occurs.
        # The TTS service receives and processes the full, unmodified text.
        # ==========================================================================

        client = TTSClient(base_url=tts_base_url or DEFAULT_TTS_BASE)

        audio_segments = []
        segment_durations = []  # List of (article_index, duration) tuples
        all_scripts = []  # List of all scripts for transcript

        # Generate intro
        intro_text = f"Good {datetime.now().strftime('%I:%M %p')}. Here's your local news update for {location}."
        all_scripts.append(intro_text)
        logger.info(f"Generating intro audio: {len(intro_text)} chars")
        intro_audio = client.synthesize_wav(intro_text, voice=voice, timeout=1800)  # 30 min timeout per segment
        if intro_audio:
            intro_path = os.path.join(temp_dir, "intro.wav")
            with open(intro_path, 'wb') as f:
                f.write(intro_audio)
            try:
                intro_clip = AudioFileClip(intro_path)
                intro_duration = intro_clip.duration
                intro_clip.close()
                audio_segments.append(intro_path)
                segment_durations.append(("intro", intro_duration))
                logger.info(f"Intro audio: {intro_duration:.2f} seconds")
            except Exception:
                logger.warning("Failed to get intro duration, skipping")
        
        # Generate audio for each article
        for i, article in enumerate(articles):
            logger.info(f"Generating audio for article {i+1}/{len(articles)}: {article.id}")

            # Generate script for this article
            article_script = generate_article_script(
                article, location, base_url=base_url, model=model, timeout_s=300
            )

            if not article_script:
                # Fallback: use article title and first few sentences
                title = article.ai_title or article.source_title or "Untitled"
                body = (article.ai_body or article.raw_content or "")
                # Get first 3 sentences or 500 chars, whichever is less
                sentences = body.split('.')[:3] if body else []
                body_text = '. '.join(s.strip() for s in sentences if s.strip())
                if body_text and not body_text.endswith('.'):
                    body_text += '.'
                article_script = f"{title}. {body_text}"
                logger.info(f"Using fallback script for article {article.id}: {len(article_script)} chars")

            # Always include full script in transcript
            all_scripts.append(article_script)
            script_total_chars = len(article_script)
            script_total_words = len(article_script.split())
            logger.info(f"Article {i+1} script: {script_total_chars} chars, {script_total_words} words")
            logger.info(f">>> GENERATING TTS WITH AUTO-CHUNKING FOR COMPLETE AUDIO <<<")

            # Generate TTS with automatic chunking fallback
            # - First tries complete text in one request
            # - If audio is truncated (< 70% expected), automatically chunks and concatenates
            # - Ensures 100% of text is converted to audio
            result = _generate_tts_with_chunking(
                client=client,
                text=article_script,
                voice=voice,
                timeout=2700,  # 45 min timeout
                temp_dir=temp_dir,
                segment_name=f"article_{article.id}"
            )

            if not result:
                logger.error(f"CRITICAL: Failed to generate TTS for article {article.id} even with chunking")
                logger.error(f"Article script was: {script_total_chars} chars, {script_total_words} words")
                logger.error(f"Article {i+1} will be SKIPPED from broadcast (no audio)")
                # Do NOT add to segment_durations - this article will be excluded from the video
                # Do NOT add estimated duration - it causes misalignment
                continue

            article_audio, article_duration = result

            # Save article audio
            article_audio_path = os.path.join(temp_dir, f"article_{article.id}.wav")
            with open(article_audio_path, 'wb') as f:
                f.write(article_audio)

            audio_file_size = len(article_audio)
            logger.info(f"Article {i+1} final audio: {article_duration:.2f}s, {audio_file_size:,} bytes")
            logger.info(f"✓ Article {i+1} COMPLETE AUDIO GENERATED (100% of text)")

            audio_segments.append(article_audio_path)
            segment_durations.append((i, article_duration))
        
        # Generate weather audio
        if weather_report:
            all_scripts.append(weather_report)
            logger.info(f"Generating weather audio: {len(weather_report)} chars")
            logger.info(f">>> GENERATING TTS WITH AUTO-CHUNKING FOR COMPLETE AUDIO <<<")

            result = _generate_tts_with_chunking(
                client=client,
                text=weather_report,
                voice=voice,
                timeout=2700,
                temp_dir=temp_dir,
                segment_name="weather"
            )

            if not result:
                logger.error(f"CRITICAL: Failed to generate weather TTS even with chunking")
                logger.error(f"Weather segment will be SKIPPED from broadcast (no audio)")
                # Do NOT add to segment_durations - weather will be excluded from the video
                # Do NOT add estimated duration - it causes misalignment
            else:
                weather_audio, weather_duration = result

                weather_audio_path = os.path.join(temp_dir, "weather.wav")
                with open(weather_audio_path, 'wb') as f:
                    f.write(weather_audio)

                audio_file_size = len(weather_audio)
                logger.info(f"Weather final audio: {weather_duration:.2f}s, {audio_file_size:,} bytes")
                logger.info(f"✓ Weather COMPLETE AUDIO GENERATED (100% of text)")

                audio_segments.append(weather_audio_path)
                segment_durations.append(("weather", weather_duration))
        
        # Generate ending
        ending_text = "That's all for this broadcast. Thank you for watching, and have a great day!"
        all_scripts.append(ending_text)
        logger.info(f"Generating ending audio: {len(ending_text)} chars")
        ending_audio = client.synthesize_wav(ending_text, voice=voice, timeout=1800)  # 30 min timeout
        if ending_audio:
            ending_path = os.path.join(temp_dir, "ending.wav")
            with open(ending_path, 'wb') as f:
                f.write(ending_audio)
            try:
                ending_clip = AudioFileClip(ending_path)
                ending_duration = ending_clip.duration
                ending_clip.close()
                audio_segments.append(ending_path)
                segment_durations.append(("ending", ending_duration))
                logger.info(f"Ending audio: {ending_duration:.2f} seconds")
            except Exception:
                logger.warning("Failed to get ending duration, skipping")
        
        # FINAL VALIDATION: Check completeness
        logger.info("=" * 80)
        logger.info("FINAL AUDIO GENERATION SUMMARY:")
        logger.info(f"  - Total scripts: {len(all_scripts)}")
        logger.info(f"  - Total audio segments: {len(audio_segments)}")
        logger.info(f"  - Segment durations tracked: {len(segment_durations)}")

        # Count how many segments have actual audio files
        actual_audio_count = len(audio_segments)
        expected_audio_count = len(articles) + 2  # articles + intro + ending
        if weather_report:
            expected_audio_count += 1  # +weather

        logger.info(f"  - Expected audio segments: {expected_audio_count}")
        logger.info(f"  - Actual audio files: {actual_audio_count}")

        if actual_audio_count < expected_audio_count:
            missing = expected_audio_count - actual_audio_count
            logger.error(f"CRITICAL: {missing} audio segment(s) are MISSING!")
            logger.error("The broadcast will have GAPS where no audio plays!")
        else:
            logger.info("✓ ALL AUDIO SEGMENTS GENERATED SUCCESSFULLY")

        # Validate all audio files exist and are non-empty
        for i, seg_path in enumerate(audio_segments):
            if not os.path.exists(seg_path):
                logger.error(f"CRITICAL: Audio file missing: {seg_path}")
            else:
                file_size = os.path.getsize(seg_path)
                if file_size < 1000:
                    logger.error(f"CRITICAL: Audio file too small ({file_size} bytes): {seg_path}")
                else:
                    logger.info(f"  ✓ Segment {i+1}/{len(audio_segments)}: {os.path.basename(seg_path)} ({file_size:,} bytes)")

        logger.info("=" * 80)

        # Combine all audio segments
        if not audio_segments:
            logger.error("No audio segments generated")
            return None

        logger.info(f"Combining {len(audio_segments)} audio segments")
        audio_clips = []
        for seg_path in audio_segments:
            try:
                clip = AudioFileClip(seg_path)
                audio_clips.append(clip)
            except Exception as e:
                logger.warning(f"Failed to load audio segment {seg_path}: {e}")
        
        if not audio_clips:
            logger.error("No valid audio clips to combine")
            return None
        
        # Concatenate all audio clips
        final_audio = concatenate_audioclips(audio_clips)
        
        # Write combined audio
        final_audio.write_audiofile(output_path, verbose=False, logger=None)
        
        total_duration = final_audio.duration
        
        # Cleanup
        final_audio.close()
        for clip in audio_clips:
            clip.close()
        
        logger.info(f"Combined audio saved: {total_duration:.2f} seconds total")
        return (segment_durations, all_scripts, total_duration)
        
    except Exception as e:
        logger.error(f"generate_broadcast_audio_segments failed: {e}", exc_info=True)
        return None


def compile_broadcast_video(
    articles: List[Article],
    article_image_paths: Dict[int, str],
    weather_slide_path: Optional[str],
    radar_card_path: Optional[str],  # NEW: Additional radar weather card
    intro_slide_path: Optional[str],
    ending_slide_path: Optional[str],
    audio_path: str,
    segment_durations: List[Tuple],  # List of (article_index, duration) or ("intro", duration) or ("weather", duration) or ("ending", duration)
    all_scripts: List[str],  # List of scripts for each segment (for captions)
    output_path: str,
    base_dir: str,
    width: int = 1280,
    height: int = 720
) -> Optional[Tuple[float, Optional[str]]]:
    """Compile video slideshow with proper timing for each segment. Returns duration in seconds.

    Sync policy:
    - Build an absolute timeline anchored to the narration audio length.
    - Each visual segment is positioned with set_start(current_time) and set_duration(seg_duration).
    - This avoids cumulative rounding errors from sequential concatenation.
    - Optionally fade-in segments for polish without changing alignment.
    """
    try:
        # Load audio
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
        
        # We'll build a set of timeline-aligned clips and composite them
        timeline_clips = []
        current_time = 0.0
        
        # Create a mapping of article index to article object
        article_map = {i: article for i, article in enumerate(articles)}
        
        # Helper function to resize image with PIL (fixes ANTIALIAS issue)
        def resize_image_with_pil(image_path: str, target_width: int, target_height: int) -> str:
            """Resize image using PIL and return path to resized image."""
            try:
                img = Image.open(image_path)

                # Convert palette (P) and RGBA images to RGB to avoid JPEG save errors
                if img.mode in ('P', 'RGBA', 'LA', 'PA'):
                    # Create white background for transparency
                    if img.mode in ('RGBA', 'LA', 'PA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA', 'PA') else None)
                        img = background
                    else:
                        # Simple palette conversion
                        img = img.convert('RGB')

                # Use LANCZOS instead of ANTIALIAS (deprecated in newer Pillow)
                # Handle both old and new Pillow versions
                try:
                    # Try new Pillow 10+ API first
                    resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                except AttributeError:
                    # Fallback to old Pillow API (Image.LANCZOS)
                    try:
                        resized = img.resize((target_width, target_height), Image.LANCZOS)
                    except AttributeError:
                        # Last resort: use default resampling
                        resized = img.resize((target_width, target_height))

                # Determine output format based on original file extension
                base_name = os.path.basename(image_path)
                temp_path = os.path.join(tempfile.gettempdir(), f"resized_{os.getpid()}_{base_name}")

                # Save with appropriate format
                if base_name.lower().endswith('.png'):
                    resized.save(temp_path, format='PNG')
                else:
                    # Convert to RGB if not already for JPEG
                    if resized.mode != 'RGB':
                        resized = resized.convert('RGB')
                    resized.save(temp_path, format='JPEG', quality=95)

                return temp_path
            except Exception as e:
                logger.warning(f"Failed to resize image {image_path}: {e}")
                return image_path
        
        # Helper function to create article title overlay with white background
        def create_title_overlay_image(title: str, width: int, height: int) -> str:
            """Create a title overlay image with white background and black bold text."""
            try:
                # Try to load a font
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
                except Exception:
                    try:
                        font = ImageFont.truetype("arial.ttf", 36)
                    except Exception:
                        font = ImageFont.load_default()
                
                # Calculate text dimensions with wrapping
                max_width = width - 80  # Leave margins
                max_height = height // 6  # Max 1/6 of image height
                padding = 20
                
                # Split text into words and wrap
                words = title.split()
                lines = []
                current_line = []
                
                for word in words:
                    test_line = ' '.join(current_line + [word])
                    # Get text size
                    bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), test_line, font=font)
                    text_width = bbox[2] - bbox[0]
                    
                    if text_width <= max_width - (padding * 2):
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                            current_line = [word]
                        else:
                            # Single word is too long, split it
                            current_line.append(word)
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                # Limit to 2 lines max
                if len(lines) > 2:
                    lines = lines[:2]
                    lines[-1] = lines[-1][:50] + "..." if len(lines[-1]) > 50 else lines[-1]
                
                # Calculate overlay dimensions
                line_heights = []
                for line in lines:
                    bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), line, font=font)
                    line_heights.append(bbox[3] - bbox[1])
                
                total_text_height = sum(line_heights) + (len(lines) - 1) * 10  # 10px spacing between lines
                overlay_height = total_text_height + (padding * 2)
                overlay_width = min(max_width, width - 40)  # Leave 20px margins on each side
                
                # Create overlay image with transparent background and semi-transparent dark panel
                overlay = Image.new('RGBA', (overlay_width, overlay_height), color=(0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay, 'RGBA')
                # Panel background (rounded), semi-transparent black
                try:
                    draw.rounded_rectangle(
                        [(0, 0), (overlay_width, overlay_height)],
                        radius=16,
                        fill=(0, 0, 0, 160)
                    )
                except Exception:
                    draw.rectangle([(0, 0), (overlay_width, overlay_height)], fill=(0, 0, 0, 160))
                
                # Draw text
                y_offset = padding
                for i, line in enumerate(lines):
                    # Center text horizontally
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    x_offset = (overlay_width - text_width) // 2
                    draw.text((x_offset, y_offset), line, fill=(255, 255, 255, 255), font=font)
                    y_offset += line_heights[i] + 10
                
                # Save overlay
                overlay_path = os.path.join(tempfile.gettempdir(), f"title_overlay_{os.getpid()}_{hash(title)}.png")
                overlay.save(overlay_path, 'PNG')
                return overlay_path
            except Exception as e:
                logger.warning(f"Failed to create title overlay: {e}")
                return None
        
        # Process each segment: create clips aligned to absolute timeline
        for seg_index, segment_info in enumerate(segment_durations):
            if isinstance(segment_info, tuple) and len(segment_info) == 2:
                seg_type, seg_duration = segment_info

                if seg_type == "intro":
                    # Use intro slide if available
                    if intro_slide_path and os.path.exists(intro_slide_path):
                        try:
                            clip = ImageClip(intro_slide_path, duration=seg_duration)
                            # Align to timeline and add gentle fade-in
                            try:
                                TRANSITION_DURATION = float(os.environ.get("BROADCAST_TRANSITION_DURATION", "0.5"))
                            except Exception:
                                TRANSITION_DURATION = 0.5
                            clip = clip.set_start(current_time).set_duration(seg_duration)
                            if seg_index > 0 and TRANSITION_DURATION > 0:
                                clip = clip.crossfadein(TRANSITION_DURATION)
                            timeline_clips.append(clip)
                        except Exception as e:
                            logger.warning(f"Failed to create intro clip: {e}")
                    else:
                        # Fallback placeholder
                        try:
                            intro_img = Image.new('RGB', (width, height), color='#1e293b')
                            intro_path = os.path.join(tempfile.gettempdir(), f"intro_{os.getpid()}.png")
                            intro_img.save(intro_path)
                            clip = ImageClip(intro_path, duration=seg_duration)
                            try:
                                TRANSITION_DURATION = float(os.environ.get("BROADCAST_TRANSITION_DURATION", "0.5"))
                            except Exception:
                                TRANSITION_DURATION = 0.5
                            clip = clip.set_start(current_time).set_duration(seg_duration)
                            if seg_index > 0 and TRANSITION_DURATION > 0:
                                clip = clip.crossfadein(TRANSITION_DURATION)
                            timeline_clips.append(clip)
                        except Exception:
                            pass

                elif seg_type == "ending":
                    # Use ending slide if available
                    if ending_slide_path and os.path.exists(ending_slide_path):
                        try:
                            clip = ImageClip(ending_slide_path, duration=seg_duration)
                            try:
                                TRANSITION_DURATION = float(os.environ.get("BROADCAST_TRANSITION_DURATION", "0.5"))
                            except Exception:
                                TRANSITION_DURATION = 0.5
                            clip = clip.set_start(current_time).set_duration(seg_duration)
                            if seg_index > 0 and TRANSITION_DURATION > 0:
                                clip = clip.crossfadein(TRANSITION_DURATION)
                            timeline_clips.append(clip)
                        except Exception as e:
                            logger.warning(f"Failed to create ending clip: {e}")
                    else:
                        # Fallback placeholder
                        try:
                            ending_img = Image.new('RGB', (width, height), color='#1e293b')
                            ending_path = os.path.join(tempfile.gettempdir(), f"ending_{os.getpid()}.png")
                            ending_img.save(ending_path)
                            clip = ImageClip(ending_path, duration=seg_duration)
                            try:
                                TRANSITION_DURATION = float(os.environ.get("BROADCAST_TRANSITION_DURATION", "0.5"))
                            except Exception:
                                TRANSITION_DURATION = 0.5
                            clip = clip.set_start(current_time).set_duration(seg_duration)
                            if seg_index > 0 and TRANSITION_DURATION > 0:
                                clip = clip.crossfadein(TRANSITION_DURATION)
                            timeline_clips.append(clip)
                        except Exception:
                            pass

                elif seg_type == "weather":
                    # Add BOTH weather slides: regular weather report + radar card
                    # Split duration between them
                    slide_duration = seg_duration / 2

                    # First: Regular weather report slide
                    if weather_slide_path and os.path.exists(weather_slide_path):
                        try:
                            resized_path = resize_image_with_pil(weather_slide_path, width, height)
                            weather_clip = ImageClip(resized_path, duration=slide_duration)
                            try:
                                TRANSITION_DURATION = float(os.environ.get("BROADCAST_TRANSITION_DURATION", "0.5"))
                            except Exception:
                                TRANSITION_DURATION = 0.5
                            weather_clip = weather_clip.set_start(current_time).set_duration(slide_duration)
                            if seg_index > 0 and TRANSITION_DURATION > 0:
                                weather_clip = weather_clip.crossfadein(TRANSITION_DURATION)
                            timeline_clips.append(weather_clip)
                            logger.info(f"Added weather slide (duration: {slide_duration:.2f}s)")
                        except Exception as e:
                            logger.warning(f"Failed to create weather slide: {e}")

                    # Second: Radar weather card
                    if radar_card_path and os.path.exists(radar_card_path):
                        try:
                            resized_path = resize_image_with_pil(radar_card_path, width, height)
                            radar_clip = ImageClip(resized_path, duration=slide_duration)
                            try:
                                TRANSITION_DURATION = float(os.environ.get("BROADCAST_TRANSITION_DURATION", "0.5"))
                            except Exception:
                                TRANSITION_DURATION = 0.5
                            radar_clip = radar_clip.set_start(current_time + slide_duration).set_duration(slide_duration)
                            if TRANSITION_DURATION > 0:
                                radar_clip = radar_clip.crossfadein(TRANSITION_DURATION)
                            timeline_clips.append(radar_clip)
                            logger.info(f"Added radar card (duration: {slide_duration:.2f}s)")
                        except Exception as e:
                            logger.warning(f"Failed to create radar card: {e}")

                    # If neither slide exists, add placeholder
                    if (not weather_slide_path or not os.path.exists(weather_slide_path)) and \
                       (not radar_card_path or not os.path.exists(radar_card_path)):
                        try:
                            placeholder = Image.new('RGB', (width, height), color='#1e293b')
                            placeholder_path = os.path.join(tempfile.gettempdir(), f"weather_placeholder_{os.getpid()}.png")
                            placeholder.save(placeholder_path)
                            clip = ImageClip(placeholder_path, duration=seg_duration)
                            try:
                                TRANSITION_DURATION = float(os.environ.get("BROADCAST_TRANSITION_DURATION", "0.5"))
                            except Exception:
                                TRANSITION_DURATION = 0.5
                            clip = clip.set_start(current_time).set_duration(seg_duration)
                            if seg_index > 0 and TRANSITION_DURATION > 0:
                                clip = clip.crossfadein(TRANSITION_DURATION)
                            timeline_clips.append(clip)
                        except Exception:
                            pass

                elif isinstance(seg_type, int) and seg_type in article_map:
                    # Article segment
                    article = article_map[seg_type]
                    image_path = article_image_paths.get(article.id)
                    
                    if image_path and os.path.exists(image_path):
                        try:
                            # Resize with PIL first to avoid ANTIALIAS issue
                            resized_path = resize_image_with_pil(image_path, width, height)
                            clip = ImageClip(resized_path, duration=seg_duration)
                            # Apply subtle Ken Burns effect (slow zoom) for visual interest
                            try:
                                kb_flag = str(os.environ.get("BROADCAST_KEN_BURNS", "1")).strip().lower() in ("1", "true", "yes", "on")
                                kb_zoom = float(os.environ.get("BROADCAST_KEN_BURNS_ZOOM", "0.03"))  # ~3% zoom over clip
                            except Exception:
                                kb_flag = True
                                kb_zoom = 0.03
                            if kb_flag and seg_duration and seg_duration > 0.1:
                                try:
                                    clip = clip.resize(lambda t: 1.0 + (kb_zoom * (t / max(seg_duration, 0.0001))))
                                except Exception as e:
                                    logger.debug(f"Ken Burns effect skipped: {e}")

                            # Add title overlay with white background at top
                            title = article.ai_title or article.source_title or "News Story"
                            overlay_path = create_title_overlay_image(title, width, height)

                            if overlay_path and os.path.exists(overlay_path):
                                try:
                                    overlay_clip = ImageClip(overlay_path, duration=seg_duration)
                                    # Position at top center with small margin
                                    overlay_clip = overlay_clip.set_position(('center', 20))
                                    clip = CompositeVideoClip([clip, overlay_clip])
                                except Exception as e:
                                    logger.warning(f"Failed to add title overlay: {e}")

                            # Align to absolute timeline and fade-in
                            try:
                                TRANSITION_DURATION = float(os.environ.get("BROADCAST_TRANSITION_DURATION", "0.5"))
                            except Exception:
                                TRANSITION_DURATION = 0.5
                            clip = clip.set_start(current_time).set_duration(seg_duration)
                            if seg_index > 0 and TRANSITION_DURATION > 0:
                                clip = clip.crossfadein(TRANSITION_DURATION)
                            timeline_clips.append(clip)
                        except Exception as e:
                            logger.warning(f"Failed to create clip for article {article.id}: {e}")
                            # Fallback placeholder
                            try:
                                placeholder = Image.new('RGB', (width, height), color='#334155')
                                placeholder_path = os.path.join(tempfile.gettempdir(), f"placeholder_{article.id}_{os.getpid()}.png")
                                placeholder.save(placeholder_path)
                                clip = ImageClip(placeholder_path, duration=seg_duration)
                                try:
                                    TRANSITION_DURATION = float(os.environ.get("BROADCAST_TRANSITION_DURATION", "0.5"))
                                except Exception:
                                    TRANSITION_DURATION = 0.5
                                clip = clip.set_start(current_time).set_duration(seg_duration)
                                if seg_index > 0 and TRANSITION_DURATION > 0:
                                    clip = clip.crossfadein(TRANSITION_DURATION)
                                timeline_clips.append(clip)
                            except Exception:
                                pass
                    else:
                        # Create placeholder slide
                        try:
                            placeholder = Image.new('RGB', (width, height), color='#334155')
                            placeholder_path = os.path.join(tempfile.gettempdir(), f"placeholder_{article.id}_{os.getpid()}.png")
                            placeholder.save(placeholder_path)
                            clip = ImageClip(placeholder_path, duration=seg_duration)
                            try:
                                TRANSITION_DURATION = float(os.environ.get("BROADCAST_TRANSITION_DURATION", "0.5"))
                            except Exception:
                                TRANSITION_DURATION = 0.5
                            clip = clip.set_start(current_time).set_duration(seg_duration)
                            if seg_index > 0 and TRANSITION_DURATION > 0:
                                clip = clip.crossfadein(TRANSITION_DURATION)
                            timeline_clips.append(clip)
                        except Exception:
                            pass

                current_time += seg_duration

        if not timeline_clips:
            # Fallback: create a simple placeholder
            placeholder = Image.new('RGB', (width, height), color='#1e293b')
            placeholder_path = os.path.join(tempfile.gettempdir(), f"broadcast_placeholder_{os.getpid()}.png")
            placeholder.save(placeholder_path)
            clip = ImageClip(placeholder_path, duration=total_duration)
            timeline_clips.append(clip.set_start(0).set_duration(total_duration))

        # Compose final video on an absolute timeline with a solid background
        logger.info(f"Compositing {len(timeline_clips)} video clips on absolute timeline")
        try:
            bg_color = (30, 41, 59)  # slate-800-ish
            background = ColorClip(size=(width, height), color=bg_color).set_duration(total_duration)
            final_video = CompositeVideoClip([background] + timeline_clips, size=(width, height))
        except Exception as e:
            logger.warning(f"Composite failed, falling back to simple concatenation: {e}")
            # Fallback to simple concatenation if composite fails
            final_video = concatenate_videoclips(timeline_clips, method="compose")
        # Ensure exact duration matches audio to avoid drift
        try:
            final_video = final_video.set_duration(total_duration)
        except Exception:
            pass
        
        # Add animated reporter GIF overlay in bottom corner (talking head effect)
        # Look for reporter GIF in broadcast directory
        reporter_gif_path = os.path.join(base_dir, "reporter.gif")
        if not os.path.exists(reporter_gif_path):
            # Also check for common alternative names/locations
            alt_paths = [
                os.path.join(base_dir, "reporter_avatar.gif"),
                os.path.join(base_dir, "talking_head.gif"),
                os.path.join(base_dir, "news_reporter.gif"),
            ]
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    reporter_gif_path = alt_path
                    break
            
            # If still not found, try to create/download one
            if not os.path.exists(reporter_gif_path):
                logger.info("Reporter GIF not found, attempting to create one")
                if download_reporter_gif(reporter_gif_path):
                    logger.info("Successfully created reporter GIF")
                else:
                    logger.warning("Failed to create reporter GIF, will skip talking head overlay")
        
        if os.path.exists(reporter_gif_path):
            try:
                logger.info("Adding animated reporter GIF overlay")
                
                # Pre-resize GIF using PIL to avoid ANTIALIAS issues in MoviePy
                avatar_size = 180
                try:
                    # Load and resize GIF with PIL first
                    gif_img = Image.open(reporter_gif_path)
                    
                    # Handle animated GIF
                    frames = []
                    durations = []
                    try:
                        while True:
                            # Get frame duration (in milliseconds)
                            frame_duration = gif_img.info.get('duration', 100)  # Default 100ms
                            durations.append(frame_duration)
                            
                            # Resize frame using LANCZOS (not ANTIALIAS)
                            try:
                                resized_frame = gif_img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                            except AttributeError:
                                # Fallback for older Pillow
                                try:
                                    resized_frame = gif_img.resize((avatar_size, avatar_size), Image.LANCZOS)
                                except AttributeError:
                                    resized_frame = gif_img.resize((avatar_size, avatar_size))
                            
                            frames.append(resized_frame.copy())
                            gif_img.seek(gif_img.tell() + 1)
                    except EOFError:
                        pass  # End of GIF
                    
                    # Save resized GIF to temp file
                    resized_gif_path = os.path.join(tempfile.gettempdir(), f"resized_reporter_{os.getpid()}.gif")
                    if frames:
                        try:
                            # Use durations list if available, otherwise use single default value
                            if durations and len(durations) == len(frames):
                                # PIL accepts a list of durations for each frame
                                frames[0].save(
                                    resized_gif_path,
                                    save_all=True,
                                    append_images=frames[1:],
                                    duration=durations,
                                    loop=0,
                                    optimize=False  # Disable optimization to avoid corruption
                                )
                            else:
                                # Use default duration for all frames
                                frames[0].save(
                                    resized_gif_path,
                                    save_all=True,
                                    append_images=frames[1:],
                                    duration=100,
                                    loop=0,
                                    optimize=False  # Disable optimization to avoid corruption
                                )
                            
                            # Verify the saved file is valid
                            if os.path.exists(resized_gif_path):
                                file_size = os.path.getsize(resized_gif_path)
                                if file_size > 0:
                                    # Try to open and verify it's a valid GIF
                                    try:
                                        test_img = Image.open(resized_gif_path)
                                        test_img.verify()
                                        test_img.close()
                                        reporter_gif_path = resized_gif_path
                                        logger.info(f"Pre-resized GIF to {avatar_size}x{avatar_size} using PIL (verified: {file_size} bytes)")
                                    except Exception as verify_err:
                                        logger.warning(f"Resized GIF verification failed: {verify_err}, using original GIF")
                                        # Clean up invalid file
                                        try:
                                            os.remove(resized_gif_path)
                                        except Exception:
                                            pass
                                else:
                                    logger.warning(f"Resized GIF file is empty, using original GIF")
                                    try:
                                        os.remove(resized_gif_path)
                                    except Exception:
                                        pass
                            else:
                                logger.warning(f"Resized GIF file not created, using original GIF")
                        except Exception as save_err:
                            logger.warning(f"Failed to save resized GIF: {save_err}, using original GIF")
                            try:
                                if os.path.exists(resized_gif_path):
                                    os.remove(resized_gif_path)
                            except Exception:
                                pass
                except Exception as pil_err:
                    logger.warning(f"Failed to pre-resize GIF with PIL: {pil_err}, will let MoviePy handle it")
                
                # Load GIF as video clip (MoviePy handles GIFs)
                # Use original path if resizing failed
                try:
                    reporter_clip = VideoFileClip(reporter_gif_path, has_mask=True)
                except Exception as load_err:
                    logger.warning(f"Failed to load resized GIF {reporter_gif_path}: {load_err}, trying original")
                    # Fall back to original GIF path if resized version failed
                    original_path = os.path.join(base_dir, "reporter.gif")
                    if os.path.exists(original_path) and original_path != reporter_gif_path:
                        reporter_clip = VideoFileClip(original_path, has_mask=True)
                    else:
                        raise
                
                # Resize to appropriate size (if not already resized)
                if reporter_clip.size[0] != avatar_size or reporter_clip.size[1] != avatar_size:
                    reporter_clip = reporter_clip.resize((avatar_size, avatar_size))
                
                # Ensure GIF plays throughout the entire video duration
                # This includes all segments: intro, articles, weather, ending
                gif_duration = reporter_clip.duration
                logger.info(f"GIF duration: {gif_duration:.2f}s, Video duration: {total_duration:.2f}s")
                
                if gif_duration < total_duration:
                    # Calculate how many loops needed to cover the entire video
                    loops_needed = int(total_duration / gif_duration) + 2  # Add extra loop to ensure coverage
                    logger.info(f"Looping GIF {loops_needed} times to cover {total_duration:.2f}s")
                    
                    # Create multiple copies of the GIF
                    gif_clips = [reporter_clip] * loops_needed
                    reporter_clip = concatenate_videoclips(gif_clips)
                    
                    # Trim to exact video duration (ensures it plays throughout all speaking)
                    reporter_clip = reporter_clip.subclip(0, total_duration)
                    logger.info(f"GIF trimmed to exact video duration: {reporter_clip.duration:.2f}s")
                else:
                    # If GIF is longer than video, trim to match video duration
                    reporter_clip = reporter_clip.subclip(0, total_duration)
                    logger.info(f"GIF trimmed to match video duration: {reporter_clip.duration:.2f}s")
                
                # Ensure the clip duration matches the final video exactly
                if abs(reporter_clip.duration - total_duration) > 0.1:
                    logger.warning(f"GIF duration mismatch: {reporter_clip.duration:.2f}s vs {total_duration:.2f}s, adjusting")
                    reporter_clip = reporter_clip.subclip(0, min(reporter_clip.duration, total_duration))
                
                # Position in bottom right corner with margin
                reporter_clip = reporter_clip.set_position((width - avatar_size - 20, height - avatar_size - 20))
                
                # Set the clip to play for the entire duration (ensures it's visible during all speaking)
                reporter_clip = reporter_clip.set_duration(total_duration)
                
                # Composite with main video - this will overlay the GIF throughout the entire video
                final_video = CompositeVideoClip([final_video, reporter_clip])
                logger.info(f"Animated reporter GIF added successfully, playing for {total_duration:.2f}s (full video duration)")
            except Exception as e:
                logger.warning(f"Failed to add reporter GIF overlay: {e}", exc_info=True)
                # Try fallback to static avatar if GIF fails
                try:
                    reporter_avatar_path = os.path.join(base_dir, "reporter_avatar.png")
                    if not os.path.exists(reporter_avatar_path):
                        create_reporter_avatar(reporter_avatar_path, width=180, height=180)
                    if os.path.exists(reporter_avatar_path):
                        avatar_clip = ImageClip(reporter_avatar_path, duration=total_duration)
                        avatar_clip = avatar_clip.resize((avatar_size, avatar_size))
                        avatar_clip = avatar_clip.set_position((width - avatar_size - 20, height - avatar_size - 20))
                        final_video = CompositeVideoClip([final_video, avatar_clip])
                        logger.info("Using static reporter avatar as fallback")
                except Exception as fallback_err:
                    logger.warning(f"Failed to add static reporter avatar: {fallback_err}")
        else:
            logger.info("No reporter GIF found - skipping talking head overlay")
            logger.info(f"To add a talking head, place an animated GIF named 'reporter.gif' in: {base_dir}")
        
        # Helper function to format time for SRT (HH:MM:SS,mmm)
        def format_srt_time(seconds: float) -> str:
            """Convert seconds to SRT time format HH:MM:SS,mmm"""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        
        # Helper function to parse SRT time format back to seconds
        def parse_srt_time(time_str: str) -> float:
            """Convert SRT time format HH:MM:SS,mmm to seconds"""
            try:
                time_part, millis_part = time_str.split(',')
                hours, minutes, seconds = map(int, time_part.split(':'))
                millis = int(millis_part)
                return hours * 3600 + minutes * 60 + seconds + (millis / 1000.0)
            except Exception:
                # Fallback: try parsing as float if format is wrong
                try:
                    return float(time_str.replace(':', '').replace(',', '.'))
                except Exception:
                    return 0.0
        
        # Helper function to split text into phrase-sized chunks for better caption timing
        def split_into_phrases(text: str, min_words: int = 3, max_words: int = 12) -> List[str]:
            """Split text into phrase-sized chunks based on word count.
            This provides better timing accuracy than sentence-based splitting."""
            import re
            # First, split on sentence boundaries
            sentences = re.split(r'([.!?]+)', text)
            sentence_list = []
            for i in range(0, len(sentences) - 1, 2):
                if i + 1 < len(sentences):
                    sentence = (sentences[i] + sentences[i + 1]).strip()
                    if sentence:
                        sentence_list.append(sentence)
            
            if not sentence_list:
                # Fallback: split by newlines or return as single sentence
                sentence_list = [s.strip() for s in text.split('\n') if s.strip()] or [text.strip()]
            
            # Now split sentences into phrase-sized chunks
            chunks = []
            for sentence in sentence_list:
                words = sentence.split()
                word_count = len(words)
                
                if word_count <= max_words:
                    # Sentence fits in one chunk
                    chunks.append(sentence)
                else:
                    # Split sentence into chunks at natural break points
                    # Try to split at commas, semicolons, or conjunctions
                    parts = re.split(r'([,;]| and | or | but )', sentence)
                    current_chunk = []
                    current_word_count = 0
                    
                    i = 0
                    while i < len(parts):
                        part = parts[i].strip()
                        if not part:
                            i += 1
                            continue
                        
                        # If this is a separator, add it to current chunk
                        if i + 1 < len(parts) and parts[i] in [',', ';', ' and ', ' or ', ' but ']:
                            if current_chunk:
                                current_chunk.append(parts[i])
                            i += 1
                            continue
                        
                        part_words = part.split()
                        part_word_count = len(part_words)
                        
                        # If adding this part would exceed max_words, start a new chunk
                        if current_word_count + part_word_count > max_words and current_chunk:
                            chunk_text = ' '.join(current_chunk).strip()
                            if len(chunk_text.split()) >= min_words:
                                chunks.append(chunk_text)
                            current_chunk = []
                            current_word_count = 0
                        
                        current_chunk.append(part)
                        current_word_count += part_word_count
                        
                        # If we've reached a good chunk size, save it
                        if current_word_count >= max_words:
                            chunk_text = ' '.join(current_chunk).strip()
                            if len(chunk_text.split()) >= min_words:
                                chunks.append(chunk_text)
                            current_chunk = []
                            current_word_count = 0
                        
                        i += 1
                    
                    # Add any remaining chunk
                    if current_chunk:
                        chunk_text = ' '.join(current_chunk).strip()
                        if len(chunk_text.split()) >= min_words:
                            chunks.append(chunk_text)
            
            return chunks if chunks else [text.strip()]
        
        # Generate SRT file from scripts and segment durations
        logger.info("Generating SRT subtitle file")
        srt_path = output_path.replace('.mp4', '.srt')
        srt_entries = []
        entry_number = 1
        current_time = 0.0
        script_index = 0
        
        # Estimated speaking rate: words per minute (adjustable based on voice)
        # Slightly lower rate for more accurate timing - accounts for natural pauses
        words_per_minute = 140.0
        
        for segment_info in segment_durations:
            if isinstance(segment_info, tuple) and len(segment_info) == 2:
                seg_type, seg_duration = segment_info
                
                if script_index < len(all_scripts):
                    script_text = all_scripts[script_index]
                    
                    if script_text.strip():
                        # Split script into phrase-sized chunks
                        phrases = split_into_phrases(script_text)
                        
                        if phrases:
                            # Calculate cumulative timing based on word count
                            cumulative_time = 0.0
                            
                            for phrase in phrases:
                                if not phrase.strip():
                                    continue
                                
                                # Calculate duration based on word count
                                word_count = len(phrase.split())
                                phrase_duration = (word_count / words_per_minute) * 60.0
                                
                                # Ensure we don't exceed segment duration
                                remaining_segment_time = seg_duration - cumulative_time
                                if phrase_duration > remaining_segment_time:
                                    phrase_duration = remaining_segment_time
                                
                                start_time = current_time + cumulative_time
                                end_time = start_time + phrase_duration
                                
                                # Ensure end_time doesn't exceed segment end
                                if end_time > current_time + seg_duration:
                                    end_time = current_time + seg_duration
                                
                                # Only add if we have valid timing
                                if start_time < end_time and phrase_duration > 0:
                                    srt_entries.append({
                                        'number': entry_number,
                                        'start': format_srt_time(start_time),
                                        'end': format_srt_time(end_time),
                                        'text': phrase.strip()
                                    })
                                    entry_number += 1
                                    cumulative_time += phrase_duration
                                    
                                    # Stop if we've used all segment time
                                    if cumulative_time >= seg_duration:
                                        break
                            
                            # Validate timing: if calculated time doesn't match segment duration, scale it
                            if cumulative_time > 0 and abs(cumulative_time - seg_duration) > 0.1:
                                # Scale the last entries to fit exactly
                                scale_factor = seg_duration / cumulative_time
                                segment_start_entries = [e for e in srt_entries if float(e['start'].replace(':', '').replace(',', '.')) >= current_time]
                                if segment_start_entries:
                                    # Recalculate timing for this segment's entries
                                    adjusted_time = 0.0
                                    for entry in segment_start_entries:
                                        original_start = parse_srt_time(entry['start'])
                                        original_end = parse_srt_time(entry['end'])
                                        original_duration = original_end - original_start
                                        
                                        adjusted_duration = original_duration * scale_factor
                                        entry['start'] = format_srt_time(current_time + adjusted_time)
                                        entry['end'] = format_srt_time(current_time + adjusted_time + adjusted_duration)
                                        adjusted_time += adjusted_duration
                    
                    script_index += 1
                
                current_time += seg_duration
        
        # Write SRT file with proper formatting
        try:
            with open(srt_path, 'w', encoding='utf-8') as f:
                for entry in srt_entries:
                    # Ensure proper SRT format
                    f.write(f"{entry['number']}\n")
                    # Clamp any end time to total_duration to avoid overshoot
                    try:
                        start_s = parse_srt_time(entry['start'])
                        end_s = min(parse_srt_time(entry['end']), total_duration)
                        start_fmt = format_srt_time(max(0.0, min(start_s, total_duration)))
                        end_fmt = format_srt_time(max(0.0, end_s))
                        f.write(f"{start_fmt} --> {end_fmt}\n")
                    except Exception:
                        f.write(f"{entry['start']} --> {entry['end']}\n")
                    # SRT text can be multi-line, but we'll keep it simple
                    text = entry['text'].strip()
                    # Remove any HTML-like tags or formatting
                    text = text.replace('<', '').replace('>', '')
                    f.write(f"{text}\n")
                    f.write("\n")  # Blank line between entries
            logger.info(f"SRT file created: {srt_path} with {len(srt_entries)} entries")
            
            # Verify SRT file was created and has content
            if os.path.exists(srt_path):
                file_size = os.path.getsize(srt_path)
                logger.info(f"SRT file verified: {file_size} bytes")
                if file_size == 0:
                    logger.warning("SRT file is empty!")
                    srt_path = None
        except Exception as e:
            logger.error(f"Failed to create SRT file: {e}", exc_info=True)
            srt_path = None
        
        # Note: We're using SRT file for captions instead of visual overlays
        
        # Optional background music with ducking
        try:
            enabled_flag = str(os.environ.get("BROADCAST_BGM_ENABLED", "")).strip().lower() in ("1", "true", "yes", "on")
        except Exception:
            enabled_flag = False
        bgm_path = None
        if enabled_flag:
            try:
                # Use explicit path if provided; otherwise fall back to bundled default
                explicit = os.environ.get("BROADCAST_BGM_PATH")
                if explicit and os.path.exists(explicit):
                    bgm_path = explicit
                else:
                    bundled = os.path.join(os.path.dirname(__file__), "static", "bgm.mp3")
                    if os.path.exists(bundled):
                        bgm_path = bundled
            except Exception:
                bgm_path = None

        # Apply gentle fade in/out on narration
        try:
            fade_s = float(os.environ.get("BROADCAST_AUDIO_FADE", "0.5"))
        except Exception:
            fade_s = 0.5
        try:
            audio_clip = audio_clip.audio_fadein(max(0.0, fade_s)).audio_fadeout(max(0.0, fade_s))
        except Exception:
            pass

        if enabled_flag and bgm_path:
            try:
                logger.info(f"Adding background music: {bgm_path}")
                try:
                    bgm_vol = float(os.environ.get("BROADCAST_BGM_VOLUME", "0.12"))
                except Exception:
                    bgm_vol = 0.12
                bgm_clip = AudioFileClip(bgm_path).volumex(bgm_vol)
                bgm_clip = audio_loop(bgm_clip, duration=total_duration)
                mixed = CompositeAudioClip([audio_clip, bgm_clip])
                final_video = final_video.set_audio(mixed)
                logger.info("Background music mixed under narration")
            except Exception as e:
                logger.warning(f"Failed to add background music: {e}")
                final_video = final_video.set_audio(audio_clip)
        else:
            # No BGM, set narration only
            logger.info("Setting narration audio track (no background music found)")
            final_video = final_video.set_audio(audio_clip)
        logger.info("Audio track set")
        
        # Write video file
        logger.info(f"Writing video file to {output_path}")
        final_video.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=os.path.join(tempfile.gettempdir(), f"temp_audio_{os.getpid()}.m4a"),
            remove_temp=True,
            verbose=False,
            logger=None
        )
        logger.info("Video file written successfully")
        
        # Cleanup
        final_video.close()
        audio_clip.close()
        
        return (total_duration, srt_path if 'srt_path' in locals() and srt_path else None)
        
    except Exception as e:
        logger.error(f"compile_broadcast_video failed: {e}", exc_info=True)
        return None


def compile_segments_into_broadcast(
    segments: List[BroadcastSegment],
    output_video_path: str,
    output_srt_path: str
) -> Optional[float]:
    """Compile individual segments into final broadcast video with aligned captions.

    Args:
        segments: List of validated BroadcastSegment objects
        output_video_path: Path for final video
        output_srt_path: Path for final SRT file

    Returns:
        Total duration in seconds, or None if failed
    """
    try:
        from moviepy.editor import VideoFileClip, concatenate_videoclips

        logger.info("=" * 80)
        logger.info(f"COMPILING {len(segments)} SEGMENTS INTO FINAL BROADCAST")
        logger.info("=" * 80)

        # Load all segment videos
        video_clips = []
        for i, segment in enumerate(segments):
            logger.info(f"Loading segment {i+1}/{len(segments)}: {segment.segment_type}")
            try:
                clip = VideoFileClip(segment.video_path)
                video_clips.append(clip)
                logger.info(f"  ✓ Loaded: {segment.duration:.2f}s")
            except Exception as e:
                logger.error(f"  ✗ Failed to load segment video: {e}")
                return None

        # Concatenate all videos
        logger.info("Concatenating video segments...")
        final_video = concatenate_videoclips(video_clips, method="compose")
        total_duration = final_video.duration

        logger.info(f"Writing final video: {output_video_path}")
        final_video.write_videofile(
            output_video_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            verbose=False,
            logger=None
        )

        # Cleanup
        final_video.close()
        for clip in video_clips:
            clip.close()

        logger.info(f"✓ Final video created: {total_duration:.2f}s")

        # Generate final SRT file with adjusted timings
        logger.info("Generating final SRT file...")

        def format_srt_time(seconds: float) -> str:
            """Convert seconds to SRT time format HH:MM:SS,mmm"""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

        srt_entries = []
        entry_id = 1
        current_time_offset = 0.0

        for segment in segments:
            for caption in segment.captions:
                # Adjust caption times based on segment position in final video
                start_time = current_time_offset + caption['start']
                end_time = current_time_offset + caption['end']

                srt_entries.append({
                    'id': entry_id,
                    'start': format_srt_time(start_time),
                    'end': format_srt_time(end_time),
                    'text': caption['text']
                })
                entry_id += 1

            current_time_offset += segment.duration

        # Write SRT file
        with open(output_srt_path, 'w', encoding='utf-8') as f:
            for entry in srt_entries:
                f.write(f"{entry['id']}\n")
                f.write(f"{entry['start']} --> {entry['end']}\n")
                f.write(f"{entry['text']}\n")
                f.write("\n")

        logger.info(f"✓ SRT file created: {len(srt_entries)} caption entries")
        logger.info("=" * 80)
        logger.info(f"✓ BROADCAST COMPILATION COMPLETE: {total_duration:.2f}s")
        logger.info("=" * 80)

        return total_duration

    except Exception as e:
        logger.error(f"Failed to compile segments: {e}", exc_info=True)
        return None


def generate_and_compile_broadcast(
    *,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    location: Optional[str] = None,
    force: bool = False
) -> Optional[Broadcast]:
    """Generate and compile a complete broadcast using SEGMENT-BY-SEGMENT approach.

    NEW APPROACH:
    1. Create intro segment (audio + video + captions) - validate alignment
    2. Create each article segment individually - validate alignment
    3. Create weather segment - validate alignment
    4. Create ending segment - validate alignment
    5. Compile all validated segments into final broadcast

    This ensures PERFECT synchronization between audio, video, and captions!

    Returns Broadcast model instance. Wrapped with 60 minute timeout."""
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
    from .progress import progress

    BROADCAST_TIMEOUT_S = 3600  # 60 minutes

    def _generate():
        session = SessionLocal()
        try:
            # Load settings
            tts_settings = session.query(TTSSettings).filter_by(id=1).one_or_none()
            if not tts_settings or not tts_settings.enabled:
                logger.warning("TTS not enabled, skipping broadcast generation")
                return None
            
            app_settings = session.query(AppSettings).filter_by(id=1).one_or_none()
            # Apply broadcast settings into environment for downstream helpers
            try:
                if app_settings:
                    # Toggle explicit enable flag for BGM, even if files exist
                    os.environ["BROADCAST_BGM_ENABLED"] = "1" if (app_settings.broadcast_bgm_enabled is True) else "0"
                    if app_settings.broadcast_transition_duration is not None:
                        os.environ["BROADCAST_TRANSITION_DURATION"] = str(app_settings.broadcast_transition_duration)
                    if app_settings.broadcast_ken_burns_enabled is not None:
                        os.environ["BROADCAST_KEN_BURNS"] = "1" if app_settings.broadcast_ken_burns_enabled else "0"
                    if app_settings.broadcast_ken_burns_zoom is not None:
                        os.environ["BROADCAST_KEN_BURNS_ZOOM"] = str(app_settings.broadcast_ken_burns_zoom)
                    if app_settings.broadcast_audio_fade is not None:
                        os.environ["BROADCAST_AUDIO_FADE"] = str(app_settings.broadcast_audio_fade)
                    if app_settings.broadcast_bgm_path:
                        os.environ["BROADCAST_BGM_PATH"] = app_settings.broadcast_bgm_path
                    if app_settings.broadcast_bgm_volume is not None:
                        os.environ["BROADCAST_BGM_VOLUME"] = str(app_settings.broadcast_bgm_volume)
            except Exception:
                pass
            
            # Resolve location using same logic as scheduler
            resolved_location = location
            if not resolved_location:
                from .scheduler import _location as scheduler_location
                resolved_location = scheduler_location()
            
            # Get recent articles (limit to 10)
            progress.phase('broadcast', 'Step 1: Gathering articles and weather data')
            articles = _get_recent_articles(limit=10, hours=48)
            if not articles and not force:
                logger.info("No recent articles, skipping broadcast generation")
                return None
            
            # Get latest weather report
            weather_report = (
                session.query(WeatherReport)
                .order_by(WeatherReport.fetched_at.desc())
                .limit(1)
                .one_or_none()
            )
            
            # Ensure directories exist
            base_dir, images_dir = _ensure_broadcast_dirs()
            
            # Create reusable intro and ending slides
            logger.info("Creating intro and ending slides")
            progress.phase('broadcast', 'Step 2: Creating intro and ending slides')
            intro_slide_path = os.path.join(base_dir, "intro_slide.png")
            ending_slide_path = os.path.join(base_dir, "ending_slide.png")
            if not os.path.exists(intro_slide_path):
                create_intro_slide(intro_slide_path, resolved_location)
            if not os.path.exists(ending_slide_path):
                create_ending_slide(ending_slide_path)
            
            # Download article images
            logger.info("Downloading article images")
            progress.phase('broadcast', 'Step 3: Downloading article images')
            article_image_paths = download_article_images(articles, images_dir)
            
            # Create weather slides (both regular and radar card)
            logger.info("Creating weather slides")
            progress.phase('broadcast', 'Step 4: Creating weather slides')
            timestamp = int(datetime.now().timestamp())
            weather_slide_path = os.path.join(base_dir, f"weather_slide_{timestamp}.png")
            radar_card_path = os.path.join(base_dir, f"radar_card_{timestamp}.png")
            create_weather_slide(weather_report, weather_slide_path)
            create_radar_weather_card(weather_report, radar_card_path)
            
            # ========================================================================
            # NEW SEGMENT-BY-SEGMENT APPROACH
            # Create each segment individually with perfect audio/video/caption alignment
            # ========================================================================

            logger.info("=" * 80)
            logger.info("SEGMENT-BY-SEGMENT BROADCAST GENERATION")
            logger.info("=" * 80)

            temp_dir = os.path.join(base_dir, f"temp_{timestamp}")
            os.makedirs(temp_dir, exist_ok=True)

            # Initialize TTS client
            tts_client = TTSClient(base_url=tts_settings.base_url)
            segments = []
            all_scripts = []

            # Step 5: Create intro segment
            progress.phase('broadcast', 'Step 5: Creating intro segment')
            intro_text = f"Good {datetime.now().strftime('%I:%M %p')}. Here's your local news update for {resolved_location}."
            all_scripts.append(intro_text)

            intro_segment = create_individual_segment(
                segment_type="intro",
                segment_id="intro",
                text=intro_text,
                image_path=intro_slide_path if os.path.exists(intro_slide_path) else None,
                title="News Update",
                temp_dir=temp_dir,
                tts_client=tts_client,
                voice=tts_settings.voice
            )

            if intro_segment:
                segments.append(intro_segment)
                logger.info(f"✓ Intro segment created: {intro_segment.duration:.2f}s")
            else:
                logger.error("Failed to create intro segment")
                return None

            # Step 6: Create article segments
            progress.phase('broadcast', f'Step 6: Creating {len(articles)} article segments')
            for i, article in enumerate(articles):
                logger.info(f"Creating article segment {i+1}/{len(articles)}")

                # Generate article script
                article_script = generate_article_script(
                    article,
                    resolved_location,
                    base_url=base_url or (app_settings.ollama_base_url if app_settings else None),
                    model=model or (app_settings.ollama_model if app_settings else None),
                    timeout_s=300
                )

                if not article_script:
                    # Fallback: use article title + first sentences
                    title = article.ai_title or article.source_title or "Untitled"
                    body = (article.ai_body or article.raw_content or "")
                    sentences = body.split('.')[:3] if body else []
                    body_text = '. '.join(s.strip() for s in sentences if s.strip())
                    if body_text and not body_text.endswith('.'):
                        body_text += '.'
                    article_script = f"{title}. {body_text}"

                all_scripts.append(article_script)

                article_segment = create_individual_segment(
                    segment_type="article",
                    segment_id=article.id,
                    text=article_script,
                    image_path=article_image_paths.get(article.id),
                    title=article.ai_title or article.source_title,
                    temp_dir=temp_dir,
                    tts_client=tts_client,
                    voice=tts_settings.voice
                )

                if article_segment:
                    segments.append(article_segment)
                    logger.info(f"✓ Article {i+1} segment created: {article_segment.duration:.2f}s")
                else:
                    logger.warning(f"Failed to create article {i+1} segment, skipping")

            # Step 7: Create weather segment
            if weather_report and weather_report.ai_report:
                progress.phase('broadcast', 'Step 7: Creating weather segment')
                all_scripts.append(weather_report.ai_report)

                weather_segment = create_individual_segment(
                    segment_type="weather",
                    segment_id="weather",
                    text=weather_report.ai_report,
                    image_path=weather_slide_path if os.path.exists(weather_slide_path) else None,
                    title="Local Weather",
                    temp_dir=temp_dir,
                    tts_client=tts_client,
                    voice=tts_settings.voice
                )

                if weather_segment:
                    segments.append(weather_segment)
                    logger.info(f"✓ Weather segment created: {weather_segment.duration:.2f}s")
                else:
                    logger.warning("Failed to create weather segment")

            # Step 8: Create ending segment
            progress.phase('broadcast', 'Step 8: Creating ending segment')
            ending_text = "That's all for this broadcast. Thank you for watching, and have a great day!"
            all_scripts.append(ending_text)

            ending_segment = create_individual_segment(
                segment_type="ending",
                segment_id="ending",
                text=ending_text,
                image_path=ending_slide_path if os.path.exists(ending_slide_path) else None,
                title="Thank You",
                temp_dir=temp_dir,
                tts_client=tts_client,
                voice=tts_settings.voice
            )

            if ending_segment:
                segments.append(ending_segment)
                logger.info(f"✓ Ending segment created: {ending_segment.duration:.2f}s")
            else:
                logger.error("Failed to create ending segment")
                return None

            # Build full transcript
            full_transcript = "\n\n".join(all_scripts)

            # Step 9: Compile all segments into final broadcast
            progress.phase('broadcast', 'Step 9: Compiling all segments into final broadcast')
            video_path = os.path.join(base_dir, f"broadcast_{timestamp}.mp4")
            srt_path = os.path.join(base_dir, f"broadcast_{timestamp}.srt")

            video_duration = compile_segments_into_broadcast(
                segments=segments,
                output_video_path=video_path,
                output_srt_path=srt_path
            )

            if not video_duration:
                logger.error("Failed to compile broadcast")
                return None
            
            # Cleanup temp directory
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            
            # Create broadcast record
            progress.phase('broadcast', 'Step 10: Finalizing broadcast')
            broadcast = Broadcast(
                created_at=get_local_now(),
                transcript=full_transcript,
                video_path=video_path,
                audio_path=None,  # Audio is embedded in video segments
                srt_path=srt_path if srt_path and os.path.exists(srt_path) else None,
                duration_seconds=video_duration,
                article_count=len([s for s in segments if s.segment_type == "article"]),
                includes_weather=any(s.segment_type == "weather" for s in segments)
            )
            session.add(broadcast)
            session.commit()
            session.refresh(broadcast)
            
            logger.info(f"Broadcast generated successfully: {broadcast.id}")
            return broadcast
            
        except Exception as e:
            logger.error(f"generate_and_compile_broadcast failed: {e}", exc_info=True)
            return None
        finally:
            session.close()
            progress.clear_timeout()
    
    # Wrap with timeout
    try:
        progress.set_timeout(BROADCAST_TIMEOUT_S)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_generate)
            try:
                return future.result(timeout=BROADCAST_TIMEOUT_S)
            except FutureTimeoutError:
                future.cancel()
                logger.error(f"Broadcast generation exceeded timeout of {BROADCAST_TIMEOUT_S} seconds")
                progress.clear_timeout()
                return None
    except Exception as e:
        logger.error(f"Broadcast generation wrapper failed: {e}", exc_info=True)
        progress.clear_timeout()
        return None
