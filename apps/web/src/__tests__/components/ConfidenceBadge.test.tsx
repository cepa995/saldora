import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfidenceBadge } from '@/components/ConfidenceBadge';

describe('ConfidenceBadge', () => {
  it('renders green "confidenceReliable" for confidence >= 75', () => {
    const { container } = render(<ConfidenceBadge confidence={85} />);
    expect(screen.getByText('confidenceReliable')).toBeInTheDocument();
    const dot = container.querySelector('.rounded-full');
    expect(dot?.className).toContain('bg-green-500');
    expect(container.firstElementChild!.className).toContain('text-green-700');
  });

  it('renders green for exactly 75', () => {
    const { container } = render(<ConfidenceBadge confidence={75} />);
    expect(screen.getByText('confidenceReliable')).toBeInTheDocument();
    const dot = container.querySelector('.rounded-full');
    expect(dot?.className).toContain('bg-green-500');
  });

  it('renders amber "confidenceReview" for confidence 50-74', () => {
    const { container } = render(<ConfidenceBadge confidence={60} />);
    expect(screen.getByText('confidenceReview')).toBeInTheDocument();
    const dot = container.querySelector('.rounded-full');
    expect(dot?.className).toContain('bg-amber-500');
    expect(container.firstElementChild!.className).toContain('text-amber-700');
  });

  it('renders amber for exactly 50', () => {
    const { container } = render(<ConfidenceBadge confidence={50} />);
    expect(screen.getByText('confidenceReview')).toBeInTheDocument();
    const dot = container.querySelector('.rounded-full');
    expect(dot?.className).toContain('bg-amber-500');
  });

  it('renders red "confidenceUnreliable" for confidence < 50', () => {
    const { container } = render(<ConfidenceBadge confidence={30} />);
    expect(screen.getByText('confidenceUnreliable')).toBeInTheDocument();
    const dot = container.querySelector('.rounded-full');
    expect(dot?.className).toContain('bg-red-500');
    expect(container.firstElementChild!.className).toContain('text-red-700');
  });

  it('renders gray with em-dash for null confidence', () => {
    const { container } = render(<ConfidenceBadge confidence={null} />);
    expect(screen.getByText('—')).toBeInTheDocument();
    const dot = container.querySelector('.rounded-full');
    expect(dot?.className).toContain('bg-gray-300');
    expect(container.firstElementChild!.className).toContain('text-gray-400');
  });

  it('rounds decimal values to correct threshold', () => {
    const { container } = render(<ConfidenceBadge confidence={74.6} />);
    expect(screen.getByText('confidenceReliable')).toBeInTheDocument();
    const dot = container.querySelector('.rounded-full');
    expect(dot?.className).toContain('bg-green-500');
  });

  it('accepts custom className', () => {
    const { container } = render(<ConfidenceBadge confidence={90} className="extra" />);
    expect(container.firstElementChild!.className).toContain('extra');
  });
});
