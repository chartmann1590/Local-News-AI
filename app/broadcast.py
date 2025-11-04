from __future__ import annotations

import os
import json
import logging
import tempfile
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

import requests
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips,
    CompositeVideoClip, TextClip
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


def _get_recent_articles(limit: int = 15, hours: int = 48) -> List[Article]:
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
    timeout_s: int = 600
) -> Optional[str]:
    """Generate a broadcast script using Ollama."""
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


def download_article_images(articles: List[Article], images_dir: str) -> Dict[int, str]:
    """Download article images and return mapping of article_id -> local_path."""
    image_paths = {}
    
    for article in articles:
        if not article.image_url:
            continue
        
        local_path = os.path.join(images_dir, f"article_{article.id}.jpg")
        
        # Skip if already downloaded
        if os.path.exists(local_path):
            image_paths[article.id] = local_path
            continue
        
        try:
            resp = requests.get(article.image_url, timeout=10, stream=True)
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
            except Exception:
                # Invalid image, remove it
                try:
                    os.remove(local_path)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Failed to download image for article {article.id}: {e}")
    
    return image_paths


def create_weather_slide(weather_report: Optional[WeatherReport], output_path: str, width: int = 1280, height: int = 720) -> bool:
    """Create a weather forecast slide image."""
    try:
        # Create blank image
        img = Image.new('RGB', (width, height), color='#1e293b')  # Dark slate background
        draw = ImageDraw.Draw(img)
        
        # Try to load a font, fallback to default if not available
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except Exception:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Title
        title = "Weather Forecast"
        draw.text((width // 2, 60), title, fill='#ffffff', font=font_large, anchor='mm')
        
        y_offset = 150
        
        if weather_report and weather_report.ai_report:
            # Display weather report text
            report_lines = weather_report.ai_report.split('\n')
            for line in report_lines[:8]:  # Limit to 8 lines
                if line.strip():
                    draw.text((width // 2, y_offset), line.strip(), fill='#e2e8f0', font=font_medium, anchor='mm')
                    y_offset += 40
        
        # Try to parse forecast JSON for additional details
        if weather_report and weather_report.forecast_json:
            try:
                forecast = json.loads(weather_report.forecast_json)
                current = forecast.get('current_weather', {})
                daily = forecast.get('daily', {})
                
                if current:
                    temp = current.get('temperature')
                    if temp is not None:
                        temp_text = f"Current: {temp:.1f}°"
                        draw.text((width // 2, y_offset + 40), temp_text, fill='#60a5fa', font=font_medium, anchor='mm')
            except Exception:
                pass
        
        img.save(output_path, 'PNG')
        return True
    except Exception as e:
        logger.error(f"create_weather_slide failed: {e}", exc_info=True)
        return False


def generate_broadcast_audio(
    script: str,
    *,
    tts_base_url: Optional[str] = None,
    voice: Optional[str] = None,
    speed: float = 1.0,
    output_path: str
) -> Optional[float]:
    """Generate TTS audio from script and save to file. Returns duration in seconds."""
    if not script:
        return None
    
    client = TTSClient(base_url=tts_base_url or DEFAULT_TTS_BASE)
    
    # Generate audio
    wav_data = client.synthesize_wav(script, voice=voice)
    if not wav_data:
        return None
    
    # Save to file
    with open(output_path, 'wb') as f:
        f.write(wav_data)
    
    # Get audio duration
    try:
        audio = AudioFileClip(output_path)
        duration = audio.duration
        audio.close()
        return duration
    except Exception:
        # Fallback: estimate duration (rough approximation)
        # Average speaking rate is ~150 words per minute
        word_count = len(script.split())
        estimated_duration = (word_count / 150.0) * 60.0
        return estimated_duration


def compile_broadcast_video(
    script: str,
    articles: List[Article],
    article_image_paths: Dict[int, str],
    weather_slide_path: Optional[str],
    audio_path: str,
    output_path: str,
    width: int = 1280,
    height: int = 720
) -> Optional[float]:
    """Compile video slideshow. Returns duration in seconds."""
    try:
        # Load audio
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
        
        # Estimate segment durations (simple approach: divide evenly)
        # We'll use article images for most of the time, then weather at the end
        num_articles = len(articles)
        weather_duration = min(30.0, total_duration * 0.2)  # Weather gets 20% or max 30 seconds
        articles_duration = total_duration - weather_duration
        
        if num_articles > 0:
            article_duration = articles_duration / num_articles
        else:
            article_duration = 0
        
        video_clips = []
        
        # Create clips for each article
        for i, article in enumerate(articles):
            image_path = article_image_paths.get(article.id)
            
            if image_path and os.path.exists(image_path):
                try:
                    clip = ImageClip(image_path, duration=article_duration)
                    clip = clip.resize((width, height))
                    # Add title overlay if available
                    title = article.ai_title or article.source_title or "News Story"
                    if len(title) > 60:
                        title = title[:57] + "..."
                    try:
                        txt_clip = TextClip(title, fontsize=40, color='white', 
                                          font='Arial-Bold', method='caption', 
                                          size=(width - 100, None), align='center')
                        txt_clip = txt_clip.set_position(('center', height - 150)).set_duration(article_duration)
                        clip = CompositeVideoClip([clip, txt_clip])
                    except Exception:
                        pass  # Skip text overlay if it fails
                    video_clips.append(clip)
                except Exception as e:
                    logger.warning(f"Failed to create clip for article {article.id}: {e}")
            else:
                # Create placeholder slide
                try:
                    placeholder = Image.new('RGB', (width, height), color='#334155')
                    placeholder_path = os.path.join(tempfile.gettempdir(), f"placeholder_{article.id}.png")
                    placeholder.save(placeholder_path)
                    
                    clip = ImageClip(placeholder_path, duration=article_duration)
                    video_clips.append(clip)
                except Exception:
                    pass
        
        # Add weather slide at the end
        if weather_slide_path and os.path.exists(weather_slide_path):
            try:
                weather_clip = ImageClip(weather_slide_path, duration=weather_duration)
                weather_clip = weather_clip.resize((width, height))
                video_clips.append(weather_clip)
            except Exception as e:
                logger.warning(f"Failed to create weather clip: {e}")
        
        if not video_clips:
            # Fallback: create a simple placeholder
            placeholder = Image.new('RGB', (width, height), color='#1e293b')
            placeholder_path = os.path.join(tempfile.gettempdir(), "broadcast_placeholder.png")
            placeholder.save(placeholder_path)
            clip = ImageClip(placeholder_path, duration=total_duration)
            video_clips.append(clip)
        
        # Concatenate all video clips
        final_video = concatenate_videoclips(video_clips, method="compose")
        
        # Set audio
        final_video = final_video.set_audio(audio_clip)
        
        # Write video file
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
        
        # Cleanup
        final_video.close()
        audio_clip.close()
        
        return total_duration
        
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
    """Generate and compile a complete broadcast. Returns Broadcast model instance."""
    session = SessionLocal()
    try:
        # Load settings
        tts_settings = session.query(TTSSettings).filter_by(id=1).one_or_none()
        if not tts_settings or not tts_settings.enabled:
            logger.warning("TTS not enabled, skipping broadcast generation")
            return None
        
        app_settings = session.query(AppSettings).filter_by(id=1).one_or_none()
        
        # Get recent articles
        articles = _get_recent_articles(limit=15, hours=48)
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
        
        if not location:
            from .geo import resolve_location
            try:
                cfg = resolve_location()
                location = cfg.location_name or "Local Area"
            except Exception:
                location = "Local Area"
        
        # Generate broadcast script
        logger.info("Generating broadcast script")
        script = generate_broadcast_script(
            articles,
            weather_report.ai_report if weather_report else None,
            location,
            base_url=base_url or (app_settings.ollama_base_url if app_settings else None),
            model=model or (app_settings.ollama_model if app_settings else None)
        )
        
        if not script:
            logger.error("Failed to generate broadcast script")
            return None
        
        # Ensure directories exist
        base_dir, images_dir = _ensure_broadcast_dirs()
        
        # Download article images
        logger.info("Downloading article images")
        article_image_paths = download_article_images(articles, images_dir)
        
        # Create weather slide
        weather_slide_path = os.path.join(base_dir, f"weather_slide_{int(datetime.now().timestamp())}.png")
        create_weather_slide(weather_report, weather_slide_path)
        
        # Generate audio
        logger.info("Generating broadcast audio")
        timestamp = int(datetime.now().timestamp())
        audio_path = os.path.join(base_dir, f"audio_{timestamp}.wav")
        duration = generate_broadcast_audio(
            script,
            tts_base_url=tts_settings.base_url,
            voice=tts_settings.voice,
            speed=tts_settings.speed or 1.0,
            output_path=audio_path
        )
        
        if not duration:
            logger.error("Failed to generate broadcast audio")
            return None
        
        # Compile video
        logger.info("Compiling broadcast video")
        video_path = os.path.join(base_dir, f"broadcast_{timestamp}.mp4")
        video_duration = compile_broadcast_video(
            script,
            articles,
            article_image_paths,
            weather_slide_path if os.path.exists(weather_slide_path) else None,
            audio_path,
            video_path,
            width=1280,
            height=720
        )
        
        if not video_duration:
            logger.error("Failed to compile broadcast video")
            return None
        
        # Create broadcast record
        broadcast = Broadcast(
            created_at=get_local_now(),
            transcript=script,
            video_path=video_path,
            audio_path=audio_path,
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

