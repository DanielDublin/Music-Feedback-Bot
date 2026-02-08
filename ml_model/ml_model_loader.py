"""
Simple ML Model Loader for Music Feedback Bot
Loads the trained SimpleML model for feedback quality prediction
"""

import os
import joblib
import numpy as np
import re
from pathlib import Path

class FeedbackQualityPredictor:
    """Predicts if feedback is good quality (Pass/Fail)"""
    
    def __init__(self, model_dir='ml_model/simple_feedback_model'):
        self.model_dir = Path(model_dir)
        self.model = None
        self.vectorizer = None
        self.loaded = False
        
    def load_model(self):
        """Load the trained model and vectorizer"""
        model_path = self.model_dir / 'model.pkl'
        vectorizer_path = self.model_dir / 'vectorizer.pkl'
        
        print(f"🔍 Current working directory: {os.getcwd()}")
        print(f"🔍 Looking for model at: {model_path.resolve()}")
        print(f"🔍 Looking for vectorizer at: {vectorizer_path.resolve()}")
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path.resolve()}")
        if not vectorizer_path.exists():
            raise FileNotFoundError(f"Vectorizer not found at {vectorizer_path.resolve()}")
        
        try:
            self.model = joblib.load(model_path)
            self.vectorizer = joblib.load(vectorizer_path)
            self.loaded = True
            print(f"✅ Model loaded successfully from {self.model_dir}")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise  # Re-raise the exception
    
    def extract_features(self, feedback_text):
        """Extract features from feedback text"""
        features = {}
        
        # Basic length features
        words = feedback_text.split()
        sentences = re.split(r'[.!?]+', feedback_text)
        
        features['word_count'] = len(words)
        features['sentence_count'] = len([s for s in sentences if s.strip()])
        features['char_count'] = len(feedback_text)
        features['avg_word_length'] = np.mean([len(word) for word in words]) if words else 0
        
        # Feature extraction logic (all the same as before)
        specific_suggestions = ['increase', 'decrease', 'remove', 'add', 'change', 'replace', 
                               'move', 'cut', 'boost', 'lower', 'raise', 'eq', 'compress', 
                               'gate', 'delay', 'recommend', 'suggest', 'try', 'learn', 
                               'practice', 'work on', 'focus on', 'improve', 'fix', 'adjust']
        
        practical_feedback = ['too quiet', 'too loud', 'too low', 'too high', 'too soft', 
                             'too hard', 'too thin', 'too thick', 'too muddy', 'too bright', 
                             'too dark', 'sounds', 'quality', 'compared to', 'vs', 'against', 
                             'clipping', 'distortion', 'noise', 'problems', 'issues', 'suffer from']
        
        problem_identification = ['clipping', 'distortion', 'noise', 'muddy', 'harsh', 
                                 'problem', 'issue', 'suffer', 'wrong', 'off', 'bad', 'poor']
        
        vague_suggestions = ['could', 'should', 'might', 'maybe', 'perhaps', 'possibly', 'consider']
        
        specific_count = sum(1 for word in specific_suggestions if word in feedback_text.lower())
        practical_count = sum(1 for phrase in practical_feedback if phrase in feedback_text.lower())
        problem_count = sum(1 for phrase in problem_identification if phrase in feedback_text.lower())
        vague_count = sum(1 for word in vague_suggestions if word in feedback_text.lower())
        
        features['has_specific_suggestions'] = int(specific_count > 0)
        features['has_practical_feedback'] = int(practical_count > 0)
        features['identifies_problems'] = int(problem_count > 0)
        features['has_vague_suggestions_only'] = int(vague_count > 0 and specific_count == 0 
                                                    and practical_count == 0 and problem_count == 0)
        
        tech_terms = ['db', 'hz', 'eq', 'reverb', 'delay', 'compression', 'compressor', 
                     'limiter', 'gate', 'sidechain', 'frequency', 'bass', 'treble', 'midrange', 
                     'stereo', 'mono', 'pan', 'automation', 'fade', 'crossfade']
        
        audio_terms = ['mix', 'master', 'track', 'channel', 'bus', 'send', 'return', 
                      'plugin', 'vst', 'daw', 'volume', 'loud', 'quiet', 'level', 'gain']
        
        instrument_terms = ['guitar', 'bass', 'drums', 'piano', 'vocals', 'synth', 
                           'strings', 'brass', 'woodwind', 'beat', 'melody', 'harmony']
        
        features['has_technical_terms'] = int(any(term in feedback_text.lower() for term in tech_terms))
        features['has_audio_terms'] = int(any(term in feedback_text.lower() for term in audio_terms))
        features['has_instrument_mentions'] = int(any(term in feedback_text.lower() for term in instrument_terms))
        
        comparative_phrases = ['compared to', 'vs', 'against', 'than the', 'relative to', 'in relation to']
        features['has_comparisons'] = int(any(phrase in feedback_text.lower() for phrase in comparative_phrases))
        
        features['has_timestamps'] = int(bool(re.search(r'\d+:\d+', feedback_text)))
        features['has_questions'] = int('?' in feedback_text)
        
        positive_words = ['amazing', 'incredible', 'stunning', 'phenomenal', 'outstanding', 
                         'exceptional', 'masterful', 'brilliant', 'perfect', 'flawless', 'professional']
        features['excessive_praise'] = int(sum(1 for word in positive_words if word in feedback_text.lower()) >= 3)
        
        generic_phrases = ['overall', 'in general', 'pretty good', 'really good', 
                          'sounds good', 'nice work', 'great job', 'well done', 'solid work']
        features['has_generic_phrases'] = int(any(phrase in feedback_text.lower() for phrase in generic_phrases))
        
        features['too_short'] = int(len(words) < 8)
        features['too_generic'] = int(feedback_text.lower().strip() in 
                                     ['good', 'nice', 'great', 'love it', 'awesome', 'amazing', 'incredible'])
        
        features['timestamps_but_vague'] = int(features['has_timestamps'] and 
                                              not features['has_specific_suggestions'] and 
                                              not features['has_practical_feedback'] and 
                                              not features['has_technical_terms'])
        
        return features
    
    def predict(self, feedback_text):
        """Predict if feedback is Pass or Fail quality"""
        if not self.loaded:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        try:
            features = self.extract_features(feedback_text)
            feature_array = np.array([list(features.values())])
            
            tfidf_features = self.vectorizer.transform([feedback_text]).toarray()
            combined_features = np.hstack([feature_array, tfidf_features])
            
            prediction = self.model.predict(combined_features)[0]
            probabilities = self.model.predict_proba(combined_features)[0]
            confidence = max(probabilities)
            
            label = "Pass" if prediction == 1 else "Fail"
            is_good = prediction == 1
            
            return {
                'prediction': label,
                'probability': confidence,
                'is_good': is_good
            }
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            raise  # Re-raise the exception

# Global instance
_predictor = None

def get_predictor():
    """Get or create the global predictor instance"""
    global _predictor
    if _predictor is None:
        _predictor = FeedbackQualityPredictor()
        _predictor.load_model()  # This will now raise an exception if it fails
    return _predictor

async def predict_feedback_quality(feedback_text):
    """Async wrapper for prediction"""
    predictor = get_predictor()
    return predictor.predict(feedback_text)