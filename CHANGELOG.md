# Changelog

Reiteration and deeper explanation of all notable changes to this enhanced fork are documented in this file.

---

## [2.0.0] - Enhanced Edition - 2026

### 🎯 Major Features Added

  - Async downloads (aiohttp)
  	- Optional asynchronous downloader using aiohttp
	- Significantly improves throughput on high-latency connections
  - Resume support for partial files
	- Uses HTTP Range headers
	- Prevents restarting large downloads
  - Retry logic with exponential backoff
	- Configurable MAX_RETRIES
	- Exponential backoff (RETRY_BACKOFF_BASE)
  - Shared HTTP session reuse
	- Reduces connection overhead
	- Improves download efficiency
	- Faster session reuse
  - Centralized timeout configuration
	- CONNECT_TIMEOUT
	- READ_TIMEOUT
  - Consistent headers
	- User-Agent
	- Referer
	- Origin
  - Proper cookie/session handling for media requests
  - Better configurable performance tuning in config.py
	- USE_ASYNC_DOWNLOADER
	- MAX_RETRIES
	- RETRY_BACKOFF_BASE
	- Timeout settings
	- Worker tuning options
  - Better configurable performance tuning
  - Increased download speed
  - Improved bandwidth utilization
  - Resource efficiency
  - Increased parallelism controls
	- Configurable MAX_WORKERS
	- Better chunk size handling for different file sizes
  - Username detection
  - Enhanced folder naming
  - Album order preservation
  - Duplicate file URL detection
  - Enhanced file naming
  - Protection against long path issues
  - Documentation & explanation improvements
  - Code quality improvements


#### Username Detection & Enhanced Folder Naming
- **Added** `extract_profile_name()` function in `downloader.py`
  - Primary method: Finds `<a id="user_name">` element
  - Fallback 1: Searches for `<a class="user">` element
  - Fallback 2: Checks `<meta name="author">` tag
  - Fallback 3: Parses username from page title pattern
  - Returns "Unknown" if all methods fail
  
- **Modified** `extract_and_format_album_title()` in `downloader.py`
  - Changed format from `Album (ID)` to `Album (ID) [Username]`
  - Added `max_length` parameter (default: 200 characters)
  - Implemented smart truncation algorithm
  - Prioritizes album ID and username over album name when truncating

#### Duplicate File URL Detection & Sequential File Naming
- **Added** `get_album_name_for_files()` function in `downloader.py`
  - Extracts clean album name without ID/profile for file naming
  - Sanitizes invalid filesystem characters
  
- **Added** `generate_sequential_filename()` function in `downloader.py`
  - Creates sequential filenames: `Album (###).ext`
  - Auto-padding based on total file count (1-9 → single digit, 10-99 → 2 digits, etc.)
  - Smart truncation prioritizing sequential number
  - Preserves original file extensions
  
- **Modified** `download_item()` function in `downloader.py`
  - Added parameters: `album_name`, `file_number`, `total_files`
  - Generates sequential filename instead of using URL-based name
  - Extracts file extension from original URL

#### Order Preservation
- **Modified** `extract_download_links()` in `downloader.py`
  - Changed from set comprehension to ordered list with duplicate checking
  - Processes images first, then videos (as they appear in HTML)
  - Maintains exact album sequence for numbering
  - Prevents duplicates while preserving order

#### Parallel Execution Enhancement
- **Added** `run_in_parallel_ordered()` function in `download_utils.py`
  - New parallel execution wrapper for sequential file naming
  - Passes `file_number` and `total_files` to download function
  - Maintains parallel download speed with sequential numbering
  - Calculates 1-indexed file numbers for each task

- **Kept** Original `run_in_parallel()` function for backwards compatibility

### ⚡ Performance Optimizations

#### Configuration Changes (`config.py`)

**Worker & Concurrency Settings:**
- **Changed** `MAX_WORKERS`: 2 → `min(16, CPU_CORES * 2)`
  - Now CPU-aware with intelligent scaling
  - 8x more concurrent downloads on typical systems
  - Capped at 16 for stability

**Chunk Size Optimizations:**
- **Changed** `LARGE_FILE_CHUNK_SIZE`: 16 KB → 1 MB (64x larger)
- **Changed** `THRESHOLDS`:
  - `(1 MB, 2 KB)` → `(1 MB, 64 KB)` - 32x increase
  - `(10 MB, 4 KB)` → `(10 MB, 128 KB)` - 32x increase  
  - `(100 MB, 8 KB)` → `(100 MB, 256 KB)` - 32x increase

**Timeout Settings:**
- **Added** `CONNECT_TIMEOUT = 10` (connection establishment)
- **Changed** `READ_TIMEOUT`: 20s → 30s (50% increase)
- **Modified** `configure_session()` to use config timeout values

**New Constants:**
- **Added** `MAX_FILENAME_LENGTH = 200` (max folder/file name length)

### 🔧 Technical Improvements

#### Import Changes
- **Added** imports in `downloader.py`:
  - `READ_TIMEOUT` from `src.config`
  - `CONNECT_TIMEOUT` from `src.config`
  - `run_in_parallel_ordered` from `src.download_utils`

#### Function Signature Changes
- **Modified** `configure_session()` in `downloader.py`:
  - Changed `timeout: int = 10` → `timeout: int = CONNECT_TIMEOUT`
  - Changed `read_timeout: int = 20` → `read_timeout: int = READ_TIMEOUT`

- **Modified** `extract_and_format_album_title()` in `downloader.py`:
  - Added `album_id: str` parameter
  - Added `max_length: int = 200` parameter
  - Returns formatted title with ID and username

- **Modified** `download_item()` in `downloader.py`:
  - Added `album_name: str` parameter
  - Added `file_number: int` parameter
  - Added `total_files: int` parameter

- **Modified** `download_album()` in `downloader.py`:
  - Calls `get_album_name_for_files()` for file naming
  - Passes album name to parallel execution
  - Uses `run_in_parallel_ordered()` instead of `run_in_parallel()`

### 📝 Documentation Improvements
- **Added** Comprehensive docstrings with Args and Returns sections
- **Added** Inline comments explaining smart truncation logic
- **Added** Function purpose documentation for new features

---

## Performance Impact

### Measured Improvements
- **Download Speed**: 8% faster (1m 47s → 1m 38s in testing)
- **Bandwidth Utilization**: Significantly improved with larger chunks
- **Resource Efficiency**: Better CPU core utilization

### Test Conditions
- Album: 15 files (mixed images and videos)
- Connection: 100 Mbps broadband
- System: Windows 10, Intel i7, 16GB RAM

---

## Breaking Changes

### None for End Users
All changes are backwards compatible from a user perspective:
- Same command-line interface
- Same file structure
- Same requirements.txt

### For Developers/Forkers
If you've modified the original code:

1. **`extract_and_format_album_title()` signature changed**
   - Old: `extract_and_format_album_title(soup, album_id) -> str`
   - New: `extract_and_format_album_title(soup, album_id, max_length=200) -> str`

2. **`download_item()` signature changed**
   - Old: `download_item(download_link, task_id, live_manager, download_path, album_url)`
   - New: `download_item(download_link, task_id, live_manager, download_path, album_url, album_name, file_number, total_files)`

3. **`extract_download_links()` behavior changed**
   - Old: Returns set (unordered, no duplicates)
   - New: Returns list (ordered, no duplicates)

4. **`download_album()` calls new parallel function**
   - Old: `run_in_parallel(...)`
   - New: `run_in_parallel_ordered(...)`

---

## Known Issues

### New Issues Introduced
None identified. All enhancements maintain stability of original codebase.

### Existing Issues (Inherited from Original)
- Albums with identical names may conflict

---

## Future Enhancements Being Considered

- [ ] Create GUI interface
- [ ] Add download queue management
- [ ] Create download scheduler
- [ ] Add cloud storage integration

---

## Technical Debt Addressed

### Code Quality Improvements
- ✅ Added comprehensive docstrings
- ✅ Implemented consistent error handling
- ✅ Improved function modularity
- ✅ Enhanced code readability

### Performance Optimizations
- ✅ Eliminated inefficient set operations
- ✅ Optimized chunk sizing strategy
- ✅ Improved worker pool management
- ✅ Enhanced timeout handling

---

## Dependencies

### No Changes
All dependencies remain exactly as in the original:
- beautifulsoup4
- requests  
- rich
- aiohttp (optional)
- aiofiles (optional)

### Version Compatibility
Tested with:
- Python 3.10, 3.11, 3.12
- beautifulsoup4 4.12+
- requests 2.31+
- rich 13.0+

---

## Testing Notes

### Manual Testing Performed
- ✅ Single album downloads
- ✅ Multiple album downloads
- ✅ Profile downloads
- ✅ Custom path downloads
- ✅ Username detection (all fallback methods)
- ✅ Sequential file naming (1-999+ files)
- ✅ Smart truncation (short, medium, long names)
- ✅ Order preservation
- ✅ Performance benchmarks
- ✅ Duplicate files handling

### Edge Cases Tested
- ✅ Albums with no username available
- ✅ Albums with very long names (>200 chars)
- ✅ Albums with special characters in names
- ✅ Albums with 1000+ files
- ✅ Mixed image and video content
- ✅ Duplicate file URLs in album

---

## Credits

### Original Author
- **Lysagxra** - Original Erome Downloader
- Repository: https://github.com/Lysagxra/EromeDownloader

---

**Last Updated**: 2026
