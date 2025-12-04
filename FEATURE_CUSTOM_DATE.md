# Custom Date Processing Feature

## Overview
The WebScribe FTPS Workflow System now supports manual date specification via command-line arguments, allowing users to process files for any specific date instead of being limited to yesterday's date.

## Usage

### Default Behavior (Yesterday's Date)
```bash
python src/main.py
```
Processes files from yesterday's date (default behavior).

### Specify Custom Date
```bash
python src/main.py --date 2025-12-01
```
Processes files for December 1, 2025.

### Process Today's Files
```bash
python src/main.py --date today
```
Processes files for the current date.

### View Help
```bash
python src/main.py --help
```
Displays usage information and examples.

## Date Format
- **YYYY-MM-DD**: Standard date format (e.g., 2025-12-01, 2025-11-30)
- **today**: Special keyword for current date

## How It Works

1. **Command-Line Parsing**: The system parses the `--date` argument at startup
2. **Date Validation**: Validates the date format and converts it to a datetime object
3. **Date Folder Creation**: Creates a folder with the specified date (format: YYYY-MM-DD)
4. **File Filtering**: Downloads only files modified on the specified date
5. **CSV Generation**: Generates CSV with filename matching the date (YYYYMMDD_output.csv)

## Implementation Details

### Modified Files
1. **src/main.py**
   - Added `argparse` for command-line argument parsing
   - Added `parse_arguments()` function
   - Added `parse_date_argument()` function for date validation
   - Updated `main()` to handle custom date parameter

2. **src/controller/main_controller.py**
   - Updated `__init__()` to accept `custom_date` parameter
   - Modified `_create_date_folder()` to use custom date when provided

3. **src/utils/processing_log_creator.py**
   - Updated status display: "Pending" → "Done" for WOLF SFTP Upload
   - Updated status display: "Sent"/"Failed" → "Done" for Email Notification

## Examples

### Process Files from Last Week
```bash
python src/main.py --date 2025-11-27
```

### Process Files from Specific Month
```bash
# Process each day of November 2025
python src/main.py --date 2025-11-01
python src/main.py --date 2025-11-02
# ... and so on
```

### Reprocess Today's Files
```bash
python src/main.py --date today
```

## Error Handling

### Invalid Date Format
```bash
python src/main.py --date 12/01/2025
```
**Output**: `Error: Invalid date format: '12/01/2025'. Use YYYY-MM-DD format or 'today'`

### Invalid Date
```bash
python src/main.py --date 2025-13-45
```
**Output**: `Error: Invalid date format: '2025-13-45'. Use YYYY-MM-DD format or 'today'`

## Benefits

✅ **Flexibility**: Process files from any date, not just yesterday
✅ **Reprocessing**: Easily reprocess files from specific dates
✅ **Testing**: Test the system with specific dates
✅ **Catch-up**: Process missed dates when system was down
✅ **Validation**: Built-in date format validation

## Backward Compatibility

The feature is fully backward compatible. Running without the `--date` argument maintains the original behavior (processing yesterday's files).

## Future Enhancements

Potential future improvements:
- Date range processing (--start-date and --end-date)
- Batch processing for multiple dates
- Date exclusion patterns
- Automatic gap detection and processing

## Technical Notes

- The custom date overrides the `USE_YESTERDAY_DATE` configuration
- Date folder format remains consistent: YYYY-MM-DD
- File filtering by modification date still applies
- All other workflow steps remain unchanged
- Scheduler continues to use configured CRON/interval settings

## Support

For issues or questions about this feature, please refer to the main README.md or contact the development team.
