# AI-Based Fact Checking for News AI

## Overview

News AI now includes **AI-based fact-checking verification** to ensure that rewritten articles maintain factual accuracy. When articles are rewritten for clarity and brevity, the system automatically verifies that all facts, dates, names, numbers, and events remain accurate.

## How It Works

### 1. **Article Rewrite Process**
When an article is rewritten by the AI:
- The original article content is sent to the AI for rewriting
- The AI rewrites the article with improved clarity and structure
- **NEW**: A fact-checking verification step validates the rewrite

### 2. **Fact-Checking Verification**
The verification process checks:
- ✅ **Names** of people, organizations, and locations (must match exactly)
- ✅ **Dates and times** (must be identical)
- ✅ **Numbers and statistics** (must not be altered)
- ✅ **Key events and facts** (must remain unchanged)
- ✅ **Quotes** (if present, must be accurate)

The AI can change **wording, structure, and length**, but **facts must remain unchanged**.

### 3. **Verification Results**
The fact-checker returns:
- `accurate` (boolean): Whether the rewrite is factually correct
- `confidence` (0-1): How confident the AI is in its assessment
- `issues` (list): Any factual discrepancies found
- `details` (string): Explanation of the verification

### 4. **Decision Logic**
- **High confidence failure** (confidence > 0.7): Rewrite is **rejected**, fallback to original
- **Low confidence failure**: Warning logged, but rewrite is **accepted**
- **Success**: Rewrite is accepted with verification metadata

## Configuration

### Enable/Disable Fact-Checking

**Environment Variable**: `ENABLE_FACT_CHECKING`

**Default**: `true` (enabled)

**Options**:
- `true`, `1`, `yes` → Fact-checking enabled
- `false`, `0`, `no` → Fact-checking disabled

### Set in `.env` file:
```bash
# Enable AI fact-checking (recommended)
ENABLE_FACT_CHECKING=true

# Disable for faster processing (not recommended)
# ENABLE_FACT_CHECKING=false
```

### Set in `docker-compose.yml`:
```yaml
environment:
  - ENABLE_FACT_CHECKING=${ENABLE_FACT_CHECKING:-true}
```

## Performance Impact

### With Fact-Checking Enabled:
- **Extra time per article**: ~2-3 minutes (AI verification call)
- **Total time per article**: ~5-8 minutes (rewrite + verification)
- **Benefit**: Ensures factual accuracy, prevents misinformation

### With Fact-Checking Disabled:
- **Time per article**: ~3-5 minutes (rewrite only)
- **Risk**: Potential factual inaccuracies in rewrites

## Log Messages

### Successful Verification
```
INFO app.ai: Verifying factual accuracy of rewrite...
INFO app.ai: Fact-check: accurate=True, confidence=0.95
INFO app.ai: ✓ Fact-check passed: All facts verified accurate
```

### Failed Verification (High Confidence)
```
INFO app.ai: Verifying factual accuracy of rewrite...
INFO app.ai: Fact-check: accurate=False, confidence=0.85
WARNING app.ai: Fact-check FAILED: Found factual discrepancies
WARNING app.ai: Issues found: Date mismatch (original: 2024-11-05, rewrite: 2024-11-06)
```

### Uncertain Verification (Low Confidence)
```
INFO app.ai: Verifying factual accuracy of rewrite...
INFO app.ai: Fact-check: accurate=False, confidence=0.45
WARNING app.ai: Fact-check uncertain: Unable to verify with high confidence
```

## Examples

### Example 1: Correct Rewrite (Accepted)

**Original Article:**
> "President Joe Biden announced on November 5, 2024, that the unemployment rate dropped to 3.8% last month, marking a significant economic milestone."

**Rewritten Article:**
> "On November 5, 2024, President Joe Biden revealed that unemployment fell to 3.8% in the previous month—a major economic achievement."

**Verification Result:**
```json
{
  "accurate": true,
  "confidence": 0.95,
  "issues": [],
  "details": "All facts verified: dates, names, and numbers match"
}
```
✅ **Result**: Rewrite accepted

---

### Example 2: Incorrect Rewrite (Rejected)

**Original Article:**
> "The fire started at approximately 3:00 AM on Main Street, displacing 25 residents."

**Rewritten Article:**
> "A fire broke out around 4:00 AM on Main Street, forcing 30 people from their homes."

**Verification Result:**
```json
{
  "accurate": false,
  "confidence": 0.90,
  "issues": [
    "Time mismatch: 3:00 AM vs 4:00 AM",
    "Number mismatch: 25 residents vs 30 people"
  ],
  "details": "Found 2 factual discrepancies in times and numbers"
}
```
❌ **Result**: Rewrite rejected, fallback to original source

---

### Example 3: Stylistic Changes (Accepted)

**Original Article:**
> "Local business owner Jane Smith, 42, opened her bakery on Oak Avenue in 2015."

**Rewritten Article:**
> "Jane Smith, a 42-year-old entrepreneur, launched her bakery on Oak Avenue nine years ago."

**Verification Result:**
```json
{
  "accurate": true,
  "confidence": 0.88,
  "issues": [],
  "details": "Facts preserved despite stylistic changes (2015 → nine years ago)"
}
```
✅ **Result**: Rewrite accepted (stylistic rewording is fine)

## Technical Details

### Function: `verify_article_facts()`
**Location**: `app/ai.py`

**Parameters**:
- `original_content` (str): Original article text
- `rewritten_content` (str): AI-rewritten article text
- `base_url` (str, optional): Ollama API base URL
- `model` (str, optional): AI model to use
- `timeout_s` (int): Timeout in seconds (default: 120)

**Returns**: Dictionary with verification results

### Function: `rewrite_article()`
**Location**: `app/ai.py`

**New Parameter**:
- `verify_facts` (bool, optional): Enable fact-checking (default: uses `ENABLE_FACT_CHECKING` env var)

**Example Usage**:
```python
from app.ai import rewrite_article

# With fact-checking (default)
result = rewrite_article(content, title, location)

# Without fact-checking
result = rewrite_article(content, title, location, verify_facts=False)

# Result includes verification metadata
if result:
    verification = result.get("verification", {})
    print(f"Accurate: {verification.get('accurate')}")
    print(f"Confidence: {verification.get('confidence')}")
```

## Best Practices

### Recommended Settings
1. **Keep fact-checking ENABLED** for production use
2. **Monitor logs** for verification failures
3. **Review rejected rewrites** manually if needed
4. **Disable temporarily** only for testing/debugging

### When to Disable
- **Development/testing**: Faster iteration
- **Trusted sources only**: If you're 100% confident in your AI model
- **Performance critical**: When speed matters more than accuracy (not recommended)

### Monitoring
Check logs for patterns:
```bash
# Count fact-check failures
docker compose logs app | grep "Fact-check FAILED" | wc -l

# View recent verification results
docker compose logs app | grep "Fact-check:"

# Monitor verification confidence
docker compose logs app | grep "confidence="
```

## Troubleshooting

### Issue: All fact-checks fail
**Cause**: Ollama service unavailable or model issues
**Solution**: Check Ollama connectivity, verify model is loaded

### Issue: Low confidence scores
**Cause**: Complex articles or ambiguous facts
**Solution**: Review logs, adjust confidence threshold if needed

### Issue: Slow processing
**Cause**: Fact-checking adds ~2-3 minutes per article
**Solution**: Disable for testing, re-enable for production

## Future Enhancements

Potential improvements:
- [ ] Adjustable confidence thresholds
- [ ] Fact extraction and caching
- [ ] Multi-model verification (consensus)
- [ ] User-facing verification reports
- [ ] Fact-check history and statistics

## Support

For issues or questions about fact-checking:
1. Check logs: `docker compose logs -f app | grep "Fact-check"`
2. Review verification details in article metadata
3. Report issues on GitHub with example articles

---

**Last Updated**: November 6, 2024
**Feature Version**: 1.0
**Status**: ✅ Production Ready
