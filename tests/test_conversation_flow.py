"""
Steve Appointment Booker - Conversation Flow Test
This script tests the conversation flow with LLM responses.
"""

import os
import sys
import logging

# Add the parent directory to the Python path to import from backend
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
from backend.voice import get_llm_response
from backend.config import get_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_conversation_flow():
    """Test the conversation flow with OpenAI responses"""
    # Sample lead data
    lead_data = {
        'industry': 'Technology',
        'name': 'Test Lead',
        'employee_count': 0,
        'uses_mobile_devices': 'Unknown'
    }
    
    # Initialize conversation history
    conversation_history = []
    
    # Test responses for different stages
    test_inputs = [
        ("Yes, I'm interested in learning more about your services.", "introduction"),
        ("Yes, we have about 50 employees using mobile devices.", "qualification"),
        ("Tell me more about how you can help us.", "value_proposition"),
        ("That sounds interesting, but I need to think about it.", "objection_handling"),
        ("Maybe we can schedule for next week.", "appointment_setting")
    ]
    
    logger.info("Starting conversation flow test...")
    
    for user_input, stage in test_inputs:
        logger.info(f"\nTesting {stage} stage")
        logger.info(f"User: {user_input}")
        
        try:
            # Get AI response
            ai_response = get_llm_response(
                prompt=user_input,
                conversation_history=conversation_history,
                stage=stage,
                industry=lead_data['industry']
            )
            
            # Update conversation history
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": ai_response})
            
            logger.info(f"AI: {ai_response}")
            
        except Exception as e:
            logger.error(f"Error in {stage} stage: {str(e)}")
            return False
    
    logger.info("\nConversation flow test completed successfully!")
    return True

if __name__ == "__main__":
    config = get_config()
    logger.info(f"Using OpenAI API key: {config.get('LLM_API_KEY')[:10]}...")
    test_conversation_flow() 