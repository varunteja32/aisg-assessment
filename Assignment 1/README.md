# AI Singapore Technical Assessment

This repository contains my solutions for the AI Singapore Full Stack Engineer technical assessment.

## Assignment 1: Book Translation Tool

This assignment implements a Python application that downloads books from Project Gutenberg and translates them to Southeast Asian languages using the SEA-LION API.

### What it does

The application takes a book from Project Gutenberg, breaks it into manageable chunks, and translates it to one of the supported Southeast Asian languages (Indonesian, Filipino, Tamil, Thai, or Vietnamese). It handles all the messy parts like downloading, chunking text properly, and dealing with API rate limits.

### Key Features

- **Smart text chunking** that preserves document structure
- **Translation caching** to dramatically speed up repeated translations
- **Progress bar** for real-time translation status
- **Robust error handling** with exponential backoff retry mechanism
- **Rate limit compliance** with SEA-LION API's 10 requests per minute limit
- **Performance tracking** with detailed statistics

### Supported Languages

| Code | Language   |
| ---- | ---------- |
| id   | Indonesian |
| fil  | Filipino   |
| ta   | Tamil      |
| th   | Thai       |
| vi   | Vietnamese |

### Setting up

You'll need Python 3.9+ and a SEA-LION API key to run this.

1. **Navigate to the assignment directory:**

   ```bash
   cd assignment-1
   ```

2. **Set up environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Add your API key:**
   Copy `.env.example` to `.env` and add your SEA-LION API key.

### Running the application

The simplest way to run it:

```bash
python translate.py
```

This will translate the default book to Indonesian. You can customize it:

```bash
# Translate to Vietnamese instead
python translate.py --lang vi

# Save to a specific file
python translate.py --output my_translation.txt

# Use a different book
python translate.py --url "https://www.gutenberg.org/cache/epub/1342/pg1342.txt"

# Enable verbose output
python translate.py --verbose
```

### Command line options

| Flag        | What it does                          | Default                                                  |
| ----------- | ------------------------------------- | -------------------------------------------------------- |
| `--lang`    | Target language (id, fil, ta, th, vi) | `id` (Indonesian)                                        |
| `--output`  | Where to save the translation         | `translated_book.txt`                                    |
| `--url`     | Which book to translate               | `https://www.gutenberg.org/cache/epub/16317/pg16317.txt` |
| `--verbose` | Enable detailed logging               | Disabled by default                                      |

### Performance

The application includes performance optimizations that make a significant difference:

**First run (no cache):**

```
Translation completed! Output saved to translated_book.txt
Translated 573 chunks (1064580 characters)
Time taken: 6348.77 seconds (1 hour 45 minutes)
API calls: 574 (Failed: 1)
Success rate: 99.83%
Cache entries: 573
```

**Second run (using cache):**

```
Translation completed! Output saved to translated_book.txt
Translated 573 chunks (1064580 characters)
Time taken: 575.78 seconds (9.5 minutes)
API calls: 0 (Failed: 0)
Success rate: 0.0%
Cache entries: 573
```

The caching system reduces translation time by over 90% for subsequent translations of the same book!

## Assignment 2: [Title]

_Coming soon_

---

I enjoyed working on these assignments and learned a lot about the technologies involved. Let me know if you have any questions!
