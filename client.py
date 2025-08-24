from time import sleep
import os
import requests
from loguru import logger

root_url = "http://34.142.154.59.nip.io/ocr-app/process" # Correct OCR endpoint "http://34.142.154.84.nip.io/ocr-app/process",

def predict():
    """Send OCR prediction request"""
    logger.info("Sending POST request to OCR API...")
    
    # Check if image file exists
    image_path = "./images/receipt.jpg"
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return None
    
    try:
        # Open file in binary mode
        with open(image_path, "rb") as image_file:
            files = {
                "file": (
                    "receipt.jpg",           # filename
                    image_file,              # file object
                    "image/jpeg"             # MIME type
                )
            }
            
            # Send POST request to correct OCR endpoint
            response = requests.post(
                root_url,  # Correct OCR endpoint "http://34.142.154.84.nip.io/ocr-app/process",
                headers={
                    "accept": "application/json",
                },
                files=files,
                timeout=30  # Add timeout for OCR processing
            )
        
        # Check response status
        if response.status_code == 200:
            result = response.json()
            logger.success(f"OCR completed successfully!")
            logger.info(f"Found {len(result.get('texts', []))} text elements")
            
            # Log some results for debugging
            for i, text in enumerate(result.get('texts', [])[:3]):  # Show first 3 texts
                confidence = result.get('probs', [0])[i] if i < len(result.get('probs', [])) else 0
                logger.info(f"Text {i+1}: '{text}' (confidence: {confidence:.3f})")
            
            return result
        else:
            logger.error(f"Request failed with status {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return None


def continuous_requests():
    """Send continuous OCR requests"""
    logger.info("=== Starting Continuous OCR Requests ===")
    
    request_count = 0
    success_count = 0
    
    try:
        while True:
            request_count += 1
            logger.info(f"--- Request #{request_count} ---")
            
            result = predict()
            if result:
                success_count += 1
                # Check if result was cached
                cached = result.get('cached', False)
                processing_time = result.get('processing_time', 0)
                logger.info(f"Processing time: {processing_time:.3f}s, Cached: {cached}")
            
            logger.info(f"Success rate: {success_count}/{request_count} ({success_count/request_count*100:.1f}%)")
            
            sleep(0.5)  # Wait between requests
            
    except KeyboardInterrupt:
        logger.info("Stopping continuous requests...")
        logger.info(f"Final stats: {success_count}/{request_count} successful requests")

if __name__ == "__main__":

    continuous_requests()
   