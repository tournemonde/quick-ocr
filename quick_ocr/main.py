#!/usr/bin/env python3
from typing import Optional
import click
import pytesseract
from PIL import Image
import openai
from pathlib import Path
from dotenv import load_dotenv
import os
import time
import signal
import sys


FOLDER_PATH = Path("/Users/tournemonde/Desktop/questions/")
PROCESSED_FOLDER = Path("/Users/tournemonde/Desktop/processed/")
CHECK_SECONDS = 3

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle Ctrl-C gracefully"""
    global running
    click.echo("\nShutting down gracefully...")
    running = False


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
        return response.choices[0].message.content
    except Exception as e:
        raise click.ClickException(f"Error getting answer from LLM: {str(e)}")


@click.command()
@click.argument(
    "folder_path", type=click.Path(exists=True, path_type=Path), default=FOLDER_PATH
)
@click.option("--api-key", envvar="OPENAI_API_KEY", help="OpenAI API key")
@click.option(
    "--verbose", "-v", is_flag=True, help="Show detailed processing information"
)
@click.option(
    "--continuous", "-c", is_flag=True, help="Run continuously, checking for new images"
)
def main(
    folder_path: Path,
    api_key: Optional[str] = None,
    verbose: bool = False,
    continuous: bool = False,
) -> None:
    """Process all images in the specified folder and get answers from LLM."""
    # Load .env if present
    load_dotenv()
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise click.ClickException(
            "OpenAI API key is required. Set it using --api-key, OPENAI_API_KEY environment variable, or in a .env file."
        )

    # Create processed folder if it doesn't exist
    PROCESSED_FOLDER.mkdir(exist_ok=True)

    # Set up signal handler for Ctrl-C
    signal.signal(signal.SIGINT, signal_handler)

    if continuous and verbose:
        click.echo("Running in continuous mode. Press Ctrl-C to stop.")

    while running:
        # Get list of PNG files
        png_files = list(folder_path.glob("*.png"))

        if not png_files:
            if continuous:
                if verbose:
                    click.echo(
                        f"No images found. Checking again in {CHECK_SECONDS} seconds..."
                    )
                time.sleep(CHECK_SECONDS)
                continue
            else:
                break

        for image_path in png_files:
            if not running:  # Check if we should stop
                break

            question = extract_text_from_image(image_path)
            answer = get_answer_from_llm(question, api_key)
            if verbose:
                click.echo(f"\nProcessing {image_path.name}:")
                click.echo(f"Answer: {answer}")
            else:
                click.echo(answer)

            # Move the processed image to the processed folder
            try:
                image_path.rename(PROCESSED_FOLDER / image_path.name)
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
