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
    CompositeVideoClip, TextClip, VideoFileClip, transfx
)
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
    """Draw a simple weather icon based on WMO weather code."""
    icon, color, _ = _get_weather_icon_and_color(weather_code)

    # Try to use Unicode emoji fonts
    try:
        # Try to load a font that supports emoji
        font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", size)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except Exception:
            font = ImageFont.load_default()

    # Draw the icon
    draw.text((center_x, center_y), icon, fill=color, font=font, anchor='mm')


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

                        # Weather icon for current conditions
                        icon, icon_color, condition = _get_weather_icon_and_color(weather_code)
                        try:
                            icon_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 80)
                        except:
                            icon_font = ImageFont.load_default()
                        draw.text((220, current_y_start + 180), icon, fill='#FFFFFF', font=icon_font, anchor='mm')

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

                            # Weather icon
                            weather_code = weather_codes[day_idx] if day_idx < len(weather_codes) else 0
                            icon, icon_color, condition = _get_weather_icon_and_color(weather_code)
                            try:
                                icon_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
                            except:
                                icon_font = ImageFont.load_default()
                            draw.text((day_center_x, card_top + 95), icon, fill='#FFFFFF', font=icon_font, anchor='mm')

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


def _generate_tts_with_chunking(
    client: TTSClient,
    text: str,
    voice: Optional[str],
    timeout: int,
    temp_dir: str,
    segment_name: str
) -> Optional[Tuple[bytes, float]]:
    """Generate TTS audio with automatic chunking fallback.

    First tries to generate audio for complete text. If that results in
    truncated audio (< 70% expected duration), automatically chunks the text
    and concatenates audio.

    Returns: (audio_bytes, duration) or None
    """
    # Try full text first
    logger.info(f"Attempting TTS for {len(text)} chars (full text)")
    audio_bytes = client.synthesize_wav(text, voice=voice, timeout=timeout)

    if not audio_bytes:
        return None

    # Validate duration
    temp_path = os.path.join(temp_dir, f"_temp_{segment_name}.wav")
    with open(temp_path, 'wb') as f:
        f.write(audio_bytes)

    try:
        from moviepy.editor import AudioFileClip
        clip = AudioFileClip(temp_path)
        duration = clip.duration
        clip.close()

        # Check if audio is truncated
        word_count = len(text.split())
        expected_duration = (word_count / 150.0) * 60.0
        duration_ratio = duration / expected_duration if expected_duration > 0 else 1.0

        if duration_ratio >= 0.70:
            # Audio is good!
            logger.info(f"TTS successful: {duration:.2f}s (ratio: {duration_ratio:.2f}x)")
            return (audio_bytes, duration)

        # Audio is truncated - need to chunk
        logger.warning(f"TTS audio truncated ({duration_ratio:.1%}), retrying with chunking")

    except Exception as e:
        logger.warning(f"Failed to validate audio: {e}")
        # Continue to chunking attempt

    # Chunk and retry
    chunks = _smart_chunk_text(text, max_chars=1000)
    if len(chunks) == 1:
        # Couldn't chunk further, return what we have
        logger.warning("Cannot chunk further, using truncated audio")
        return (audio_bytes, duration if 'duration' in locals() else 0.0)

    logger.info(f"Retrying with {len(chunks)} chunks")
    chunk_audio_files = []

    for chunk_idx, chunk in enumerate(chunks):
        logger.info(f"Generating chunk {chunk_idx+1}/{len(chunks)}: {len(chunk)} chars")
        chunk_audio = client.synthesize_wav(chunk, voice=voice, timeout=timeout)

        if not chunk_audio:
            logger.error(f"Chunk {chunk_idx+1} failed to generate")
            # Clean up and return None
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

    # Concatenate all chunks
    try:
        from moviepy.editor import AudioFileClip, concatenate_audioclips

        logger.info(f"Concatenating {len(chunk_audio_files)} audio chunks")
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

        logger.info(f"✓ Chunked audio concatenated: {total_duration:.2f}s total")
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
                word_count = len(article_script.split())
                estimated_duration = (word_count / 150.0) * 60.0
                segment_durations.append((i, estimated_duration))
                logger.error(f"Article {i+1} AUDIO IS MISSING - estimated duration: {estimated_duration:.2f} seconds")
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
                word_count = len(weather_report.split())
                estimated_duration = (word_count / 150.0) * 60.0
                segment_durations.append(("weather", estimated_duration))
                logger.error(f"Weather AUDIO IS MISSING - estimated duration: {estimated_duration:.2f} seconds")
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
    """Compile video slideshow with proper timing for each segment. Returns duration in seconds."""
    try:
        # Load audio
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
        
        video_clips = []
        current_time = 0.0
        
        # Create a mapping of article index to article object
        article_map = {i: article for i, article in enumerate(articles)}
        
        # Helper function to resize image with PIL (fixes ANTIALIAS issue)
        def resize_image_with_pil(image_path: str, target_width: int, target_height: int) -> str:
            """Resize image using PIL and return path to resized image."""
            try:
                img = Image.open(image_path)
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
                temp_path = os.path.join(tempfile.gettempdir(), f"resized_{os.getpid()}_{os.path.basename(image_path)}")
                resized.save(temp_path)
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
                
                # Create overlay image with white background
                overlay = Image.new('RGB', (overlay_width, overlay_height), color='white')
                draw = ImageDraw.Draw(overlay)
                
                # Draw text
                y_offset = padding
                for i, line in enumerate(lines):
                    # Center text horizontally
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    x_offset = (overlay_width - text_width) // 2
                    draw.text((x_offset, y_offset), line, fill='black', font=font)
                    y_offset += line_heights[i] + 10
                
                # Save overlay
                overlay_path = os.path.join(tempfile.gettempdir(), f"title_overlay_{os.getpid()}_{hash(title)}.png")
                overlay.save(overlay_path, 'PNG')
                return overlay_path
            except Exception as e:
                logger.warning(f"Failed to create title overlay: {e}")
                return None
        
        # Process each segment
        for segment_info in segment_durations:
            if isinstance(segment_info, tuple) and len(segment_info) == 2:
                seg_type, seg_duration = segment_info
                
                if seg_type == "intro":
                    # Use intro slide if available
                    if intro_slide_path and os.path.exists(intro_slide_path):
                        try:
                            clip = ImageClip(intro_slide_path, duration=seg_duration)
                            video_clips.append(clip)
                        except Exception as e:
                            logger.warning(f"Failed to create intro clip: {e}")
                    else:
                        # Fallback placeholder
                        try:
                            intro_img = Image.new('RGB', (width, height), color='#1e293b')
                            intro_path = os.path.join(tempfile.gettempdir(), f"intro_{os.getpid()}.png")
                            intro_img.save(intro_path)
                            clip = ImageClip(intro_path, duration=seg_duration)
                            video_clips.append(clip)
                        except Exception:
                            pass
                
                elif seg_type == "ending":
                    # Use ending slide if available
                    if ending_slide_path and os.path.exists(ending_slide_path):
                        try:
                            clip = ImageClip(ending_slide_path, duration=seg_duration)
                            video_clips.append(clip)
                        except Exception as e:
                            logger.warning(f"Failed to create ending clip: {e}")
                    else:
                        # Fallback placeholder
                        try:
                            ending_img = Image.new('RGB', (width, height), color='#1e293b')
                            ending_path = os.path.join(tempfile.gettempdir(), f"ending_{os.getpid()}.png")
                            ending_img.save(ending_path)
                            clip = ImageClip(ending_path, duration=seg_duration)
                            video_clips.append(clip)
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
                            video_clips.append(weather_clip)
                            logger.info(f"Added weather slide (duration: {slide_duration:.2f}s)")
                        except Exception as e:
                            logger.warning(f"Failed to create weather slide: {e}")

                    # Second: Radar weather card
                    if radar_card_path and os.path.exists(radar_card_path):
                        try:
                            resized_path = resize_image_with_pil(radar_card_path, width, height)
                            radar_clip = ImageClip(resized_path, duration=slide_duration)
                            video_clips.append(radar_clip)
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
                            video_clips.append(clip)
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
                            
                            video_clips.append(clip)
                        except Exception as e:
                            logger.warning(f"Failed to create clip for article {article.id}: {e}")
                            # Fallback placeholder
                            try:
                                placeholder = Image.new('RGB', (width, height), color='#334155')
                                placeholder_path = os.path.join(tempfile.gettempdir(), f"placeholder_{article.id}_{os.getpid()}.png")
                                placeholder.save(placeholder_path)
                                clip = ImageClip(placeholder_path, duration=seg_duration)
                                video_clips.append(clip)
                            except Exception:
                                pass
                    else:
                        # Create placeholder slide
                        try:
                            placeholder = Image.new('RGB', (width, height), color='#334155')
                            placeholder_path = os.path.join(tempfile.gettempdir(), f"placeholder_{article.id}_{os.getpid()}.png")
                            placeholder.save(placeholder_path)
                            clip = ImageClip(placeholder_path, duration=seg_duration)
                            video_clips.append(clip)
                        except Exception:
                            pass
                
                current_time += seg_duration
        
        if not video_clips:
            # Fallback: create a simple placeholder
            placeholder = Image.new('RGB', (width, height), color='#1e293b')
            placeholder_path = os.path.join(tempfile.gettempdir(), f"broadcast_placeholder_{os.getpid()}.png")
            placeholder.save(placeholder_path)
            clip = ImageClip(placeholder_path, duration=total_duration)
            video_clips.append(clip)

        # Add crossfade transitions between clips (except first clip)
        logger.info(f"Adding crossfade transitions to {len(video_clips)} video clips")
        TRANSITION_DURATION = 0.5  # 0.5 second crossfade

        for i in range(len(video_clips)):
            if i > 0:
                # Add crossfade to all clips except the first
                try:
                    video_clips[i] = video_clips[i].crossfadein(TRANSITION_DURATION)
                    logger.debug(f"Added crossfade to clip {i+1}")
                except Exception as e:
                    logger.warning(f"Failed to add crossfade to clip {i+1}: {e}")

        # Concatenate all video clips
        logger.info(f"Concatenating {len(video_clips)} video clips with transitions")
        final_video = concatenate_videoclips(video_clips, method="compose")
        logger.info("Video clips concatenated successfully with crossfade transitions")
        
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
        
        # Set audio
        logger.info("Setting audio track")
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


def generate_and_compile_broadcast(
    *,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    location: Optional[str] = None,
    force: bool = False
) -> Optional[Broadcast]:
    """Generate and compile a complete broadcast. Returns Broadcast model instance.
    Wrapped with 60 minute timeout."""
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
            
            # Generate audio segments - wrapped with 60 minute timeout
            # NOTE: Each segment (intro, article, weather, ending) sends COMPLETE TEXT to TTS
            # We do NOT chunk or truncate any text - full fidelity guaranteed
            logger.info("Generating broadcast audio segments (FULL TEXT per segment)")
            progress.phase('broadcast', 'Step 5: Generating broadcast audio (FULL TEXT, 60 min timeout)')
            audio_path = os.path.join(base_dir, f"audio_{timestamp}.wav")
            temp_dir = os.path.join(base_dir, f"temp_{timestamp}")
            os.makedirs(temp_dir, exist_ok=True)

            # Wrap audio generation with 60 minute timeout
            AUDIO_TIMEOUT_S = 3600  # 60 minutes
            audio_result = None

            def _generate_audio():
                return generate_broadcast_audio_segments(
                    articles,
                    weather_report.ai_report if weather_report else None,
                    resolved_location,
                    tts_base_url=tts_settings.base_url,
                    voice=tts_settings.voice,
                    speed=tts_settings.speed or 1.0,
                    base_url=base_url or (app_settings.ollama_base_url if app_settings else None),
                    model=model or (app_settings.ollama_model if app_settings else None),
                    output_path=audio_path,
                    temp_dir=temp_dir
                )
            
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_generate_audio)
                    try:
                        audio_result = future.result(timeout=AUDIO_TIMEOUT_S)
                    except FutureTimeoutError:
                        future.cancel()
                        logger.error(f"Audio generation exceeded timeout of {AUDIO_TIMEOUT_S} seconds")
                        return None
            except Exception as e:
                logger.error(f"Audio generation wrapper failed: {e}", exc_info=True)
                return None
            
            if not audio_result:
                logger.error("Failed to generate broadcast audio")
                return None
            
            segment_durations, all_scripts, audio_duration = audio_result
            
            if not audio_duration:
                logger.error("Failed to generate broadcast audio - duration is None")
                return None
            
            # Build full transcript from all scripts
            full_transcript = "\n\n".join(all_scripts)
            
            # Compile video
            logger.info("Compiling broadcast video")
            progress.phase('broadcast', 'Step 6: Compiling broadcast video')
            video_path = os.path.join(base_dir, f"broadcast_{timestamp}.mp4")
            result = compile_broadcast_video(
                articles,
                article_image_paths,
                weather_slide_path if os.path.exists(weather_slide_path) else None,
                radar_card_path if os.path.exists(radar_card_path) else None,
                intro_slide_path if os.path.exists(intro_slide_path) else None,
                ending_slide_path if os.path.exists(ending_slide_path) else None,
                audio_path,
                segment_durations,
                all_scripts,
                video_path,
                base_dir,
                width=1280,
                height=720
            )
            
            if not result:
                logger.error("Failed to compile broadcast video")
                return None
            
            video_duration, srt_path = result
            
            # Cleanup temp directory
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            
            # Create broadcast record
            progress.phase('broadcast', 'Step 7: Finalizing broadcast')
            broadcast = Broadcast(
                created_at=get_local_now(),
                transcript=full_transcript,
                video_path=video_path,
                audio_path=audio_path,
                srt_path=srt_path if srt_path and os.path.exists(srt_path) else None,
                duration_seconds=video_duration,
                article_count=len(articles),
                includes_weather=weather_report is not None
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

