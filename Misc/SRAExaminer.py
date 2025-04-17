import re
import urllib.request
import urllib.parse
import time
import json
import random
import os

# Define bacteria-related keywords for filtering
BACTERIA_KEYWORDS = [
    # General bacteria terms
    'bacteria', 'bacterium', 'bacterial', 'prokaryote',
    
    # Common phyla
    'firmicutes', 'proteobacteria', 'actinobacteria', 'bacteroidetes',
    'cyanobacteria', 'chlamydiae', 'spirochaetes', 'tenericutes',
    
    # Common genera (add more as needed)
    'escherichia', 'salmonella', 'staphylococcus', 'streptococcus',
    'bacillus', 'clostridium', 'pseudomonas', 'mycobacterium',
    'lactobacillus', 'bifidobacterium', 'helicobacter', 'vibrio',
    'campylobacter', 'listeria', 'neisseria', 'legionella',
    'synechococcus', 'synechocystis', 'prochlorococcus',
    'nostoc', 'anabaena', 'microcystis', 'oscillatoria',
    'spirulina', 'lyngbya', 'chroococcus', 'gloeocapsa', 
    'trichodesmium', 'arthrospira',
    
    # Other common descriptors
    'microbiome', 'microbiota', 'microbial', 'metagenome',
    'gram-positive', 'gram-negative'
]

def extract_srr_ids(content):
    """Extract SRR IDs from directory listing"""
    pattern = r'SRR\d{8}'
    srr_ids = re.findall(pattern, content)
    return list(set(srr_ids))  # Remove duplicates

def fetch_with_retries(url, max_retries=5, initial_delay=1):
    """Fetch URL with exponential backoff for retries"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    delay = initial_delay
    
    for attempt in range(max_retries):
        try:
            # Add jitter to avoid synchronized requests
            jitter = random.uniform(0.1, 0.5)
            time.sleep(delay + jitter)
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                return response.read().decode('utf-8')
                
        except urllib.error.HTTPError as e:
            if e.code == 429:  # Too Many Requests
                print(f"Rate limited (429). Retry {attempt+1}/{max_retries}. Waiting {delay:.1f} seconds...")
                delay *= 2  # Exponential backoff
                continue
            else:
                print(f"HTTP Error: {e.code} for {url}")
                return None
        except Exception as e:
            print(f"Error: {str(e)} for {url}")
            if attempt < max_retries - 1:
                print(f"Retrying ({attempt+1}/{max_retries})...")
                delay *= 2
                continue
            return None
    
    print(f"Failed after {max_retries} attempts: {url}")
    return None

def fetch_organism_info_with_retry(srr_id, max_attempts=3):
    """Fetch organism info with multiple retry approaches"""
    print(f"  Fetching info for {srr_id}")
    
    # Try the simple method first
    for attempt in range(max_attempts):
        try:
            # Use esearch to get the database entry ID
            search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=sra&term={srr_id}&retmode=json"
            search_result = fetch_with_retries(search_url)
            
            if not search_result:
                print(f"  Failed to retrieve search results on attempt {attempt+1}")
                continue
            
            search_data = json.loads(search_result)
            if 'esearchresult' not in search_data or 'idlist' not in search_data['esearchresult'] or not search_data['esearchresult']['idlist']:
                print(f"  No data found on attempt {attempt+1}")
                continue
            
            uid = search_data['esearchresult']['idlist'][0]
            
            # Use efetch to get the details in XML format for more reliable parsing
            fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=sra&id={uid}&retmode=xml"
            fetch_result = fetch_with_retries(fetch_url)
            
            if not fetch_result:
                print(f"  Failed to retrieve details on attempt {attempt+1}")
                continue
            
            # Extract organism using regex
            organism_match = re.search(r'<SCIENTIFIC_NAME>([^<]+)</SCIENTIFIC_NAME>', fetch_result)
            organism = organism_match.group(1).strip() if organism_match else 'Unknown organism'
            
            # Extract study title
            study_match = re.search(r'<STUDY_TITLE>([^<]+)</STUDY_TITLE>', fetch_result)
            study_title = study_match.group(1).strip() if study_match else 'No study title available'
            
            # Extract more metadata if available
            description_match = re.search(r'<EXPERIMENT_TITLE>([^<]+)</EXPERIMENT_TITLE>', fetch_result)
            description = description_match.group(1).strip() if description_match else ''
            
            # Construct the result
            return {
                'srr_id': srr_id,
                'organism': organism,
                'study_title': study_title,
                'description': description,
                'ncbi_url': f"https://www.ncbi.nlm.nih.gov/sra/{srr_id}"
            }
            
        except Exception as e:
            print(f"  Error processing {srr_id} on attempt {attempt+1}: {str(e)}")
            # Try again with different approach if this is not the last attempt
            if attempt < max_attempts - 1:
                print(f"  Trying alternative approach...")
                time.sleep(2)  # Wait before retry
    
    # If all attempts failed
    return {'srr_id': srr_id, 'organism': 'Failed to retrieve', 'study_title': 'Failed to retrieve'}

def is_bacteria_related(info):
    """Check if the info is related to bacteria"""
    if not info or 'organism' not in info or 'study_title' not in info:
        return False
    
    # Check organism, title, and description
    text = (
        info['organism'] + ' ' + 
        info['study_title'] + ' ' + 
        info.get('description', '')
    ).lower()
    
    for term in BACTERIA_KEYWORDS:
        if term.lower() in text:
            return True
    
    # Additional check for specific bacterial taxonomic identifiers
    if any(x in info['organism'].lower() for x in ['sp.', 'strain', 'serovar']):
        # These are often bacterial strain indicators
        return True
    
    return False

def process_srr_ids(srr_ids, max_ids=None):
    """Process SRR IDs to find organism information"""
    # Limit the number of IDs if requested
    if max_ids and max_ids != 'all':
        try:
            limit = int(max_ids)
            srr_ids = srr_ids[:limit]
        except ValueError:
            print(f"Invalid limit '{max_ids}', processing all IDs")
    
    # Lists to store results
    results = []
    bacteria_results = []
    
    # Process each SRR ID
    for i, srr_id in enumerate(srr_ids):
        print(f"Processing {i+1}/{len(srr_ids)}: {srr_id}")
        
        # Get organism info
        info = fetch_organism_info_with_retry(srr_id)
        
        # Add to results
        results.append(info)
        
        # Check if it's bacteria-related
        if is_bacteria_related(info):
            info['is_bacteria'] = True
            bacteria_results.append(info)
            print(f"  MATCH! Bacteria-related: {info['organism']}")
            print(f"  Study: {info['study_title']}")
            print(f"  URL: {info['ncbi_url']}")
            print()
        else:
            info['is_bacteria'] = False
    
    return results, bacteria_results

def save_results_to_csv(results, filename):
    """Save results to a CSV file"""
    with open(filename, 'w', encoding='utf-8') as f:
        # Write header
        f.write("SRR_ID,Organism,Study_Title,Is_Bacteria,URL\n")
        
        # Write data
        for result in results:
            is_bacteria = result.get('is_bacteria', False)
            # Escape commas in fields
            organism = result.get('organism', '').replace(',', ';')
            study = result.get('study_title', '').replace(',', ';')
            url = result.get('ncbi_url', '')
            
            f.write(f"{result['srr_id']},{organism},{study},{is_bacteria},{url}\n")

def save_bacteria_results_to_txt(bacteria_results, filename):
    """Save bacteria results to a text file"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Bacteria-Related SRA Entries\n")
        f.write(f"===========================\n\n")
        f.write(f"Found {len(bacteria_results)} bacteria-related datasets\n\n")
        
        for i, result in enumerate(bacteria_results):
            f.write(f"{i+1}. {result['srr_id']}\n")
            f.write(f"   Organism: {result['organism']}\n")
            f.write(f"   Study: {result['study_title']}\n")
            f.write(f"   URL: {result['ncbi_url']}\n\n")

def main():
    try:
        # Check if paste.txt exists or ask for input
        if os.path.exists('paste.txt'):
            with open('paste.txt', 'r') as file:
                content = file.read()
            print("Read content from paste.txt")
        else:
            print("paste.txt not found. Please enter the content containing SRR IDs:")
            content = input("Paste content here (or type 'file:' followed by filename): ")
            
            if content.startswith('file:'):
                filename = content[5:].strip()
                with open(filename, 'r') as file:
                    content = file.read()
        
        # Extract SRR IDs
        srr_ids = extract_srr_ids(content)
        print(f"Found {len(srr_ids)} unique SRR IDs")
        
        if not srr_ids:
            print("No SRR IDs found in the content. Please check the input.")
            return
        
        # Ask how many to process
        max_ids = input("How many SRR IDs to process? (Enter a number or 'all'): ")
        
        # Process the SRR IDs
        results, bacteria_results = process_srr_ids(srr_ids, max_ids)
        
        # Save results to files
        save_results_to_csv(results, "sra_organism_results.csv")
        if bacteria_results:
            save_bacteria_results_to_txt(bacteria_results, "bacteria_results.txt")
        
        # Print summary
        print(f"\nFinished processing {len(results)} SRR IDs")
        print(f"Found {len(bacteria_results)} bacteria-related datasets")
        print(f"Results saved to sra_organism_results.csv")
        if bacteria_results:
            print(f"Bacteria results saved to bacteria_results.txt")
        
        # Print organism distribution
        print("\nTop organisms found:")
        organism_count = {}
        for result in results:
            organism = result.get('organism', 'Unknown')
            organism_count[organism] = organism_count.get(organism, 0) + 1
        
        # Sort by count and print top 10
        for organism, count in sorted(organism_count.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {organism}: {count}")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()