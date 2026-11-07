#!/usr/bin/env python3
import os
import signal
import time
from pathlib import Path
from typing import Optional

import click
import openai
import pytesseract
from dotenv import load_dotenv
from PIL import Image


DEFAULT_INPUT_FOLDER = Path.home() / "Desktop" / "questions"
DEFAULT_PROCESSED_FOLDER = Path.home() / "Desktop" / "processed"
CHECK_SECONDS = 3

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle Ctrl-C gracefully"""
    global running
    click.echo("\nShutting down gracefully...")
    running = False


def resolve_folder_from_env(env_name: str, fallback: Path) -> Path:
    """Resolve a folder path from an env var, falling back to a sane local default."""
    value = os.getenv(env_name)
    if not value:
        return fallback
    return Path(value).expanduser()


def extract_text_from_image(image_path: Path) -> str:
    """Extract text from an image using OCR."""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        raise click.ClickException(f"Error processing image: {str(e)}")


def get_answer_from_llm(question: str, api_key: str) -> str:
    """Get answer from OpenAI API using GPT-4 for high-quality responses."""
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4.1-nano",  # Using the latest GPT-4 model
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert academic assistant that provides detailed, accurate, and well-structured answers to exam questions. 
                    Your responses should be:
                    1. Comprehensive and thorough
                    2. Well-organized with clear explanations
                    3. Include relevant examples or evidence when appropriate
                    4. Maintain academic rigor and precision
                    5. Be completely factual with no creative interpretation""",
                },
                {"role": "user", "content": question},
            ],
            temperature=0,  # Minimum temperature for maximum determinism and factual accuracy
            max_tokens=1000,  # Allow for detailed responses
            presence_penalty=0.1,  # Slightly encourage diverse content
            frequency_penalty=0.1,  # Slightly discourage repetition
        )
        content = response.choices[0].message.content
        return content or ""
    except Exception as e:
        raise click.ClickException(f"Error getting answer from LLM: {str(e)}")


@click.command()
@click.argument("folder_path", required=False, type=click.Path(path_type=Path))
@click.option("--api-key", envvar="OPENAI_API_KEY", help="OpenAI API key")
@click.option(
    "--processed-folder",
    type=click.Path(path_type=Path),
    help="Folder where processed screenshots will be moved. Defaults to PROCESSED_FOLDER or ~/Desktop/processed.",
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Show detailed processing information"
)
@click.option(
    "--continuous", "-c", is_flag=True, help="Run continuously, checking for new images"
)
@click.option(
    "--ocr-only",
    "-o",
    is_flag=True,
    help="Only extract and print OCR text, don't send to API",
)
def main(
    folder_path: Optional[Path],
    api_key: Optional[str] = None,
    processed_folder: Optional[Path] = None,
    verbose: bool = False,
    continuous: bool = False,
    ocr_only: bool = False,
) -> None:
    """Process all images in the specified folder and get answers from LLM.

    In OCR-only mode (--ocr-only), only extracts and prints the text from images
    without sending questions to the LLM API.
    """
    # Load .env if present
    load_dotenv()

    folder_path = (folder_path or resolve_folder_from_env("SCREENSHOT_FOLDER", DEFAULT_INPUT_FOLDER)).expanduser()
    processed_folder = (processed_folder or resolve_folder_from_env("PROCESSED_FOLDER", DEFAULT_PROCESSED_FOLDER)).expanduser()

    if not folder_path.exists():
        raise click.ClickException(
            f"Screenshot folder does not exist: {folder_path}. Set SCREENSHOT_FOLDER in .env or pass the folder path as an argument."
        )

    if not folder_path.is_dir():
        raise click.ClickException(f"Screenshot folder is not a directory: {folder_path}")

    # Only require API key if not in OCR-only mode
    if not ocr_only:
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise click.ClickException(
                "OpenAI API key is required. Set it using --api-key, OPENAI_API_KEY environment variable, or in a .env file."
            )

    # Create processed folder if it doesn't exist
    processed_folder.mkdir(parents=True, exist_ok=True)

    # Set up signal handler for Ctrl-C
    signal.signal(signal.SIGINT, signal_handler)

    if continuous and verbose:
        mode_info = "OCR-only mode" if ocr_only else "full processing mode"
        click.echo(f"Running in continuous {mode_info}. Press Ctrl-C to stop.")

    if verbose:
        click.echo(f"Watching folder: {folder_path}")
        click.echo(f"Processed folder: {processed_folder}")

    while running:
        # Get list of PNG files
        png_files = list(folder_path.glob("*.png"))

        if not png_files:
            if continuous:
                # if verbose:
                #     click.echo(
                #         f"No images found. Checking again in {CHECK_SECONDS} seconds..."
                #     )
                time.sleep(CHECK_SECONDS)
                continue
            else:
                break

        for image_path in png_files:
            if not running:  # Check if we should stop
                break

            question = extract_text_from_image(image_path)
            click.echo(f"\nProcessing {image_path.name}:")
            click.echo(f"Question: {question}")

            if not ocr_only:
                answer = get_answer_from_llm(question, api_key)
                click.echo(f"Answer: {answer}")
            else:
                click.echo("OCR-only mode: Skipping API call")

            # Move the processed image to the processed folder
            try:
                image_path.rename(processed_folder / image_path.name)
                if verbose:
                    click.echo(f"Moved {image_path.name} to processed folder")
            except Exception as e:
                click.echo(
                    f"Warning: Could not move {image_path.name} to processed folder: {str(e)}"
                )

        if not continuous:
            break


if __name__ == "__main__":
    main()
