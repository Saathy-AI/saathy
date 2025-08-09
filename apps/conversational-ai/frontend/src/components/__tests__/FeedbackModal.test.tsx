import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FeedbackModal } from '../FeedbackModal';
import { chatAPI } from '../../services/api';

// Mock the API
jest.mock('../../services/api');
const mockChatAPI = chatAPI as jest.Mocked<typeof chatAPI>;

describe('FeedbackModal', () => {
  const defaultProps = {
    sessionId: 'test-session',
    onClose: jest.fn(),
    onSubmit: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders feedback form correctly', () => {
    render(<FeedbackModal {...defaultProps} />);

    expect(screen.getByText('Rate this response')).toBeInTheDocument();
    expect(screen.getByText(/How relevant was the response/)).toBeInTheDocument();
    expect(screen.getByText(/How complete was the response/)).toBeInTheDocument();
    expect(screen.getByLabelText('This response was helpful')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Tell us more about your experience...')).toBeInTheDocument();
  });

  it('displays initial score values correctly', () => {
    render(<FeedbackModal {...defaultProps} />);

    expect(screen.getByText('How relevant was the response? (80%)')).toBeInTheDocument();
    expect(screen.getByText('How complete was the response? (80%)')).toBeInTheDocument();
  });

  it('updates relevance score on slider change', () => {
    render(<FeedbackModal {...defaultProps} />);

    const relevanceSlider = screen.getAllByRole('slider')[0];
    fireEvent.change(relevanceSlider, { target: { value: '0.5' } });

    expect(screen.getByText('How relevant was the response? (50%)')).toBeInTheDocument();
  });

  it('updates completeness score on slider change', () => {
    render(<FeedbackModal {...defaultProps} />);

    const completenessSlider = screen.getAllByRole('slider')[1];
    fireEvent.change(completenessSlider, { target: { value: '0.6' } });

    expect(screen.getByText('How complete was the response? (60%)')).toBeInTheDocument();
  });

  it('toggles helpful checkbox', async () => {
    const user = userEvent.setup();
    render(<FeedbackModal {...defaultProps} />);

    const helpfulCheckbox = screen.getByLabelText('This response was helpful');
    expect(helpfulCheckbox).toBeChecked();

    await user.click(helpfulCheckbox);
    expect(helpfulCheckbox).not.toBeChecked();
  });

  it('updates feedback text', async () => {
    const user = userEvent.setup();
    render(<FeedbackModal {...defaultProps} />);

    const textarea = screen.getByPlaceholderText('Tell us more about your experience...');
    await user.type(textarea, 'Great response!');

    expect(textarea).toHaveValue('Great response!');
  });

  it('submits feedback successfully', async () => {
    mockChatAPI.submitFeedback.mockResolvedValueOnce(undefined);
    
    render(<FeedbackModal {...defaultProps} />);

    const submitButton = screen.getByText('Submit Feedback');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockChatAPI.submitFeedback).toHaveBeenCalledWith(
        'test-session',
        {
          relevance_score: 0.8,
          completeness_score: 0.8,
          helpful: true,
          feedback_text: '',
        }
      );
    });

    expect(defaultProps.onSubmit).toHaveBeenCalled();
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('shows loading state while submitting', async () => {
    // Mock a delayed response
    mockChatAPI.submitFeedback.mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    render(<FeedbackModal {...defaultProps} />);

    const submitButton = screen.getByText('Submit Feedback');
    fireEvent.click(submitButton);

    expect(screen.getByText('Submitting...')).toBeInTheDocument();
    expect(submitButton).toBeDisabled();

    await waitFor(() => {
      expect(screen.getByText('Submit Feedback')).toBeInTheDocument();
    });
  });

  it('handles submission error gracefully', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    mockChatAPI.submitFeedback.mockRejectedValueOnce(new Error('Network error'));

    render(<FeedbackModal {...defaultProps} />);

    const submitButton = screen.getByText('Submit Feedback');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to submit feedback:',
        expect.any(Error)
      );
    });

    // Modal should still be open after error
    expect(screen.getByText('Rate this response')).toBeInTheDocument();
    expect(defaultProps.onClose).not.toHaveBeenCalled();

    consoleErrorSpy.mockRestore();
  });

  it('closes modal on cancel', () => {
    render(<FeedbackModal {...defaultProps} />);

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(defaultProps.onClose).toHaveBeenCalled();
    expect(mockChatAPI.submitFeedback).not.toHaveBeenCalled();
  });

  it('submits complete feedback with all fields', async () => {
    const user = userEvent.setup();
    mockChatAPI.submitFeedback.mockResolvedValueOnce(undefined);

    render(<FeedbackModal {...defaultProps} />);

    // Adjust all fields
    const relevanceSlider = screen.getAllByRole('slider')[0];
    fireEvent.change(relevanceSlider, { target: { value: '0.9' } });

    const completenessSlider = screen.getAllByRole('slider')[1];
    fireEvent.change(completenessSlider, { target: { value: '0.7' } });

    const helpfulCheckbox = screen.getByLabelText('This response was helpful');
    await user.click(helpfulCheckbox);

    const textarea = screen.getByPlaceholderText('Tell us more about your experience...');
    await user.type(textarea, 'Could be more detailed');

    // Submit
    const submitButton = screen.getByText('Submit Feedback');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockChatAPI.submitFeedback).toHaveBeenCalledWith(
        'test-session',
        {
          relevance_score: 0.9,
          completeness_score: 0.7,
          helpful: false,
          feedback_text: 'Could be more detailed',
        }
      );
    });
  });
});