import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.guardrails.output_validator import OutputValidator

def test_output_validator():
    validator = OutputValidator()
    
    # Should flag
    res = validator.validate("your child has pneumonia")
    assert res.safe is False
    
    res = validator.validate("this is a case of bronchiolitis")
    assert res.safe is False
    
    # Should NOT flag
    res = validator.validate("your child has good color")
    assert res.safe is True
    
    res = validator.validate("symptoms that suggest pneumonia")
    assert res.safe is True
