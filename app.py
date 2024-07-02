import concurrent.futures  # Importing the module for parallel execution of tasks
from flask import Flask, request  # Importing Flask framework and request object for handling HTTP requests
from youtube_transcript_api import YouTubeTranscriptApi  # Importing YouTubeTranscriptApi for fetching YouTube video transcripts
from transformers import BartForConditionalGeneration, BartTokenizer  # Importing BART model and tokenizer from Transformers library

app = Flask(__name__)  # Creating a Flask application instance

def get_transcript(video_id, language='en'):
    # Function to fetch the transcript of a YouTube video
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
    transcript = ' '.join([d['text'] for d in transcript_list])
    return transcript

def summarize_chunk(chunk, model, tokenizer):
    # Function to summarize a chunk of text using BART model
    inputs = tokenizer.encode("summarize: " + chunk, return_tensors="pt", max_length=1024, truncation=True)
    summary_ids = model.generate(inputs, max_length=150, min_length=40, length_penalty=2.0, num_beams=4, early_stopping=True)
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

def get_summary(transcript):
    # Function to summarize the entire transcript
    if not transcript:
        return "Transcript is empty."
    
    # Initializing BART model and tokenizer
    model_name = "facebook/bart-large-cnn"
    model = BartForConditionalGeneration.from_pretrained(model_name)
    tokenizer = BartTokenizer.from_pretrained(model_name)
    
    summaries = []  # List to store summaries
    chunk_size = 3000  # Define the size of each chunk
    num_chunks = (len(transcript) + chunk_size - 1) // chunk_size  # Calculate the number of chunks
    
    # Concurrent summarization of each chunk
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []  # List to store futures
        for i in range(num_chunks):
            chunk = transcript[i * chunk_size : (i + 1) * chunk_size]  # Get a chunk of transcript
            future = executor.submit(summarize_chunk, chunk, model, tokenizer)  # Submit chunk for summarization
            futures.append(future)  # Append future object to the list
        
        # Wait for all futures to complete and collect results
        for future in concurrent.futures.as_completed(futures):
            try:
                summary_text = future.result()  # Get the result of the future
                summaries.append(summary_text)  # Append the summary to the list of summaries
            except Exception as e:
                print(f"Error processing chunk: {e}")  # Handle any exceptions that occurred
                summaries.append("Error occurred in chunk")  # Append an error message to the list of summaries
    
    return ' '.join(summaries)  # Join all summaries into a single string and return

@app.route('/summary', methods=['GET'])
def summary_api():
    # API endpoint for summarizing YouTube video transcripts
    url = request.args.get('url', '')  # Get the 'url' query parameter from the request
    video_id = url.split('=')[-1]  # Extract the video ID from the URL
    language = request.args.get('language', 'en')  # Get the 'language' query parameter (default is English)

    transcript = get_transcript(video_id, language)  # Fetch the transcript of the video
    summary = get_summary(transcript)  # Summarize the transcript
    return summary, 200  # Return the summary with HTTP status code 200 (OK)

if __name__ == '__main__':
    app.run(debug=True)  # Run the Flask application with debugging enabled
