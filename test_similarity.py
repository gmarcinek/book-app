#!/usr/bin/env python3
"""
Sentence Similarity Tester
Analyzes similarity between each sentence in a document and a target topic

FILE: test_sentence_similarity.py
"""

import re
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from ner.loaders import DocumentLoader


class SentenceSimilarityTester:
    """Test similarity of each sentence to target topics"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        print(f"🤖 Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print(f"✅ Model loaded successfully")
    
    def test_document_similarity(self, document_path: str, target_topic: str, 
                               output_dir: str = "tests/similarity") -> None:
        """
        Test document sentences against target topic
        
        Args:
            document_path: Path to document to analyze
            target_topic: Topic string to compare against
            output_dir: Directory to save results
        """
        
        print(f"📄 Loading document: {document_path}")
        
        # Load document
        loader = DocumentLoader()
        document = loader.load_document(document_path)
        text = document.content
        
        print(f"📏 Document length: {len(text):,} chars")
        
        # Extract sentences
        sentences = self._extract_sentences(text)
        print(f"📝 Extracted {len(sentences)} sentences")
        
        # Calculate similarities
        similarities = self._calculate_similarities(sentences, target_topic)
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save results
        self._save_results(sentences, similarities, target_topic, output_path, document_path)
        
        print(f"✅ Results saved to: {output_path}")
    
    def _extract_sentences(self, text: str) -> List[str]:
        """Extract sentences from text"""
        
        # Clean text first
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = text.strip()
        
        # Split by sentence endings, but be careful with abbreviations
        sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+'
        raw_sentences = re.split(sentence_pattern, text)
        
        sentences = []
        for sentence in raw_sentences:
            sentence = sentence.strip()
            
            # Filter out very short sentences (likely artifacts)
            if len(sentence) >= 20:
                # Truncate very long sentences (likely formatting issues)
                if len(sentence) > 500:
                    sentence = sentence[:500] + "..."
                
                sentences.append(sentence)
        
        return sentences
    
    def _calculate_similarities(self, sentences: List[str], target_topic: str) -> List[float]:
        """Calculate cosine similarities between sentences and target topic"""
        
        print(f"🎯 Target topic: '{target_topic}'")
        print(f"🔢 Calculating embeddings for {len(sentences)} sentences...")
        
        # Prepare texts for embedding
        all_texts = [target_topic] + sentences
        
        # Calculate embeddings in batches to avoid memory issues
        batch_size = 32
        embeddings = []
        
        for i in range(0, len(all_texts), batch_size):
            batch = all_texts[i:i + batch_size]
            batch_embeddings = self.model.encode(batch, convert_to_tensor=False)
            embeddings.extend(batch_embeddings)
            
            if i % (batch_size * 10) == 0:
                print(f"   Processed {min(i + batch_size, len(all_texts))}/{len(all_texts)} texts...")
        
        embeddings = np.array(embeddings)
        
        # Calculate similarities
        target_embedding = embeddings[0].reshape(1, -1)
        sentence_embeddings = embeddings[1:]
        
        similarities = cosine_similarity(target_embedding, sentence_embeddings)[0]
        
        print(f"✅ Calculated {len(similarities)} similarities")
        return similarities.tolist()
    
    def _save_results(self, sentences: List[str], similarities: List[float], 
                     target_topic: str, output_path: Path, document_path: str) -> None:
        """Save similarity results to file"""
        
        # Create timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"similarity_{timestamp}.txt"
        filepath = output_path / filename
        
        # Sort by similarity (highest first)
        sentence_sim_pairs = list(zip(sentences, similarities))
        sentence_sim_pairs.sort(key=lambda x: x[1], reverse=True)
        
        # Calculate statistics
        similarities_array = np.array(similarities)
        avg_sim = similarities_array.mean()
        max_sim = similarities_array.max()
        min_sim = similarities_array.min()
        std_sim = similarities_array.std()
        
        # Find high similarity sentences (>= 0.5)
        high_sim_count = sum(1 for sim in similarities if sim >= 0.5)
        medium_sim_count = sum(1 for sim in similarities if 0.3 <= sim < 0.5)
        low_sim_count = sum(1 for sim in similarities if sim < 0.3)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("SENTENCE SIMILARITY ANALYSIS\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Document: {document_path}\n")
            f.write(f"Analysis time: {datetime.now()}\n")
            f.write(f"Total sentences: {len(sentences)}\n\n")
            
            f.write(f"SZUKANY TEMAT: \"{target_topic}\"\n\n")
            
            f.write("STATISTICS:\n")
            f.write(f"  Average similarity: {avg_sim:.3f}\n")
            f.write(f"  Max similarity: {max_sim:.3f}\n")
            f.write(f"  Min similarity: {min_sim:.3f}\n")
            f.write(f"  Standard deviation: {std_sim:.3f}\n\n")
            
            f.write("DISTRIBUTION:\n")
            f.write(f"  High similarity (≥0.5): {high_sim_count} sentences\n")
            f.write(f"  Medium similarity (0.3-0.5): {medium_sim_count} sentences\n")
            f.write(f"  Low similarity (<0.3): {low_sim_count} sentences\n\n")
            
            f.write("RESULTS (sorted by similarity):\n")
            f.write("-" * 60 + "\n\n")
            
            for sentence, similarity in sentence_sim_pairs:
                # Truncate sentence for display
                short_sentence = sentence[:60] + "..." if len(sentence) > 60 else sentence
                short_sentence = short_sentence.replace('\n', ' ').replace('\r', ' ')
                
                f.write(f"[{similarity:.3f}] - {short_sentence}\n")
        
        # Also save detailed results
        detailed_filepath = output_path / f"detailed_{timestamp}.txt"
        with open(detailed_filepath, 'w', encoding='utf-8') as f:
            f.write("DETAILED SENTENCE SIMILARITY ANALYSIS\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"SZUKANY TEMAT: \"{target_topic}\"\n\n")
            
            for i, (sentence, similarity) in enumerate(sentence_sim_pairs, 1):
                f.write(f"SENTENCE {i:3d} - SIMILARITY: {similarity:.3f}\n")
                f.write("-" * 50 + "\n")
                f.write(f"{sentence}\n\n")
        
        print(f"📊 Summary:")
        print(f"   Average similarity: {avg_sim:.3f}")
        print(f"   High similarity (≥0.5): {high_sim_count}/{len(sentences)} sentences")
        print(f"   Files saved:")
        print(f"     - Summary: {filename}")
        print(f"     - Detailed: detailed_{timestamp}.txt")


def test_similarity():
    """Test function for sentence similarity"""
    
    # Initialize tester
    tester = SentenceSimilarityTester()
    
    # Test topics
    test_topics = [
        "choroba, uszczerbek na zdrowiu, szkoda, wypadek",
        "ubezpieczenie, składka, polisa, ochrona",
        "tabela, uszkodzenia ciała, procenty świadczeń",
        "reklamacja, spór, mediacja, sąd"
    ]
    
    # Document to test
    document_path = "docs/owu.pdf"
    
    for topic in test_topics:
        print(f"\n{'='*80}")
        print(f"🎯 TESTING TOPIC: {topic}")
        print(f"{'='*80}")
        
        # Clean topic name for directory
        topic_clean = re.sub(r'[^\w\s-]', '', topic).replace(' ', '_')[:30]
        output_dir = f"tests/similarity/{topic_clean}"
        
        try:
            tester.test_document_similarity(document_path, topic, output_dir)
        except Exception as e:
            print(f"❌ Error testing topic '{topic}': {e}")
    
    print(f"\n✅ All similarity tests completed!")


if __name__ == "__main__":
    test_similarity()