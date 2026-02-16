import React, { useState } from 'react';
import styles from './ContactForm.module.css';

const API_URL = 'http://34.171.83.82:8000/api/v1/leads';

export default function ContactForm(): JSX.Element {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    role: '',
    use_case: '',
    timeline: 'Immediate',
    budget: '$15K-$25K',
    interest_type: 'pilot',
  });
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('submitting');

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error('Failed to submit form');
      }

      setStatus('success');
      setMessage('Thank you! We\'ll contact you within 24 hours. Check your email for next steps.');
      setFormData({
        name: '',
        email: '',
        company: '',
        role: '',
        use_case: '',
        timeline: 'Immediate',
        budget: '$15K-$25K',
        interest_type: 'pilot',
      });
    } catch (error) {
      setStatus('error');
      setMessage('Something went wrong. Please try again or email us at mail@uapk.info');
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  return (
    <div className={styles.contactForm}>
      {status === 'success' ? (
        <div className={styles.successMessage}>
          <div className={styles.successIcon}>✅</div>
          <h3>Request Received!</h3>
          <p>{message}</p>
          <button onClick={() => setStatus('idle')} className={styles.resetButton}>
            Submit Another Request
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          <div className={styles.formHeader}>
            <h2>Ready to Deploy Agents Safely?</h2>
            <p>Get expert help from a lawyer-developer who built this for real-world compliance needs.</p>
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label>Your Name *</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                disabled={status === 'submitting'}
              />
            </div>
            <div className={styles.formGroup}>
              <label>Email *</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                disabled={status === 'submitting'}
              />
            </div>
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label>Company/Firm *</label>
              <input
                type="text"
                name="company"
                value={formData.company}
                onChange={handleChange}
                required
                disabled={status === 'submitting'}
              />
            </div>
            <div className={styles.formGroup}>
              <label>Your Role</label>
              <select
                name="role"
                value={formData.role}
                onChange={handleChange}
                disabled={status === 'submitting'}
              >
                <option value="">Select role...</option>
                <option value="General Counsel">General Counsel</option>
                <option value="Compliance Officer">Compliance Officer</option>
                <option value="CTO">CTO / Engineering Lead</option>
                <option value="Partner">Partner (Law Firm)</option>
                <option value="CEO">CEO / Founder</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>

          <div className={styles.formGroup}>
            <label>What do you want to deploy? *</label>
            <textarea
              name="use_case"
              value={formData.use_case}
              onChange={handleChange}
              rows={4}
              placeholder="e.g., Settlement negotiation agent for IP litigation cases"
              required
              disabled={status === 'submitting'}
            />
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label>Timeline</label>
              <select
                name="timeline"
                value={formData.timeline}
                onChange={handleChange}
                disabled={status === 'submitting'}
              >
                <option value="Immediate">Immediate (this month)</option>
                <option value="Next Quarter">Next Quarter</option>
                <option value="Exploring">Just Exploring</option>
              </select>
            </div>
            <div className={styles.formGroup}>
              <label>Budget Range</label>
              <select
                name="budget"
                value={formData.budget}
                onChange={handleChange}
                disabled={status === 'submitting'}
              >
                <option value="$15K-$25K">$15K-$25K (Pilot)</option>
                <option value="$5K-$10K">$5K-$10K (Blueprint)</option>
                <option value="$50K+">$50K+ (Multiple workflows)</option>
                <option value="Not sure">Not sure yet</option>
              </select>
            </div>
          </div>

          {status === 'error' && (
            <div className={styles.errorMessage}>
              {message}
            </div>
          )}

          <button
            type="submit"
            className={styles.submitButton}
            disabled={status === 'submitting'}
          >
            {status === 'submitting' ? 'Submitting...' : 'Get Expert Review'}
          </button>

          <p className={styles.privacy}>
            🔒 Your information is secure. We'll never share it with third parties.
          </p>
        </form>
      )}
    </div>
  );
}
