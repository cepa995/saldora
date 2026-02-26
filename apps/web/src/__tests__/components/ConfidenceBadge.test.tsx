import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfidenceBadge } from '@/components/ConfidenceBadge';

describe('ConfidenceBadge', () => {
  it('renders green for confidence >= 80', () => {
    const { container } = render(<ConfidenceBadge confidence={85} />);
    expect(screen.getByText('85%')).toBeInTheDocument();
    const dot = container.querySelector('.rounded-full');
    expect(dot?.className).toContain('bg-green-500');
    expect(container.firstElementChild!.className).toContain('text-green-700');
  });

  it('renders green for exactly 80', () => {
    const { container } = render(<ConfidenceBadge confidence={80} />);
    expect(screen.getByText('80%')).toBeInTheDocument();
    const dot = container.querySelector('.rounded-full');
    expect(dot?.className).toContain('bg-green-500');
  });

  it('renders amber for confidence 60-79', () => {
    const { container } = render(<ConfidenceBadge confidence={70} />);
    expect(screen.getByText('70%')).toBeInTheDocument();
    const dot = container.querySelector('.rounded-full');
    expect(dot?.className).toContain('bg-amber-500');
    expect(container.firstElementChild!.className).toContain('text-amber-700');
  });

  it('renders amber for exactly 60', () => {
    const { container } = render(<ConfidenceBadge confidence={60} />);
    expect(screen.getByText('60%')).toBeInTheDocument();
    const dot = container.querySelector('.rounded-full');
    expect(dot?.className).toContain('bg-amber-500');
  });

  it('renders red for confidence < 60', () => {
    const { container } = render(<ConfidenceBadge confidence={45} />);
    expect(screen.getByText('45%')).toBeInTheDocument();
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

  it('rounds decimal confidence values', () => {
    render(<ConfidenceBadge confidence={79.6} />);
    expect(screen.getByText('80%')).toBeInTheDocument();
  });

  it('accepts custom className', () => {
    const { container } = render(<ConfidenceBadge confidence={90} className="extra" />);
    expect(container.firstElementChild!.className).toContain('extra');
  });
});
