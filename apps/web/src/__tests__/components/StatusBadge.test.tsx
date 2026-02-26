import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '@/components/StatusBadge';
import type { InvoiceStatus } from '@/lib/types/invoice';

describe('StatusBadge', () => {
  const statuses: InvoiceStatus[] = ['processing', 'review', 'verified', 'exported', 'error'];

  it.each(statuses)('renders label for status "%s"', (status) => {
    render(<StatusBadge status={status} />);
    // The mock t() returns the key itself, so the status name is the text
    expect(screen.getByText(status)).toBeInTheDocument();
  });

  it('applies amber classes for processing status', () => {
    const { container } = render(<StatusBadge status="processing" />);
    const badge = container.firstElementChild!;
    expect(badge.className).toContain('bg-amber-50');
    expect(badge.className).toContain('text-amber-700');
  });

  it('applies blue classes for review status', () => {
    const { container } = render(<StatusBadge status="review" />);
    const badge = container.firstElementChild!;
    expect(badge.className).toContain('bg-blue-50');
    expect(badge.className).toContain('text-blue-700');
  });

  it('applies green classes for verified status', () => {
    const { container } = render(<StatusBadge status="verified" />);
    const badge = container.firstElementChild!;
    expect(badge.className).toContain('bg-green-50');
    expect(badge.className).toContain('text-green-700');
  });

  it('applies violet classes for exported status', () => {
    const { container } = render(<StatusBadge status="exported" />);
    const badge = container.firstElementChild!;
    expect(badge.className).toContain('bg-violet-50');
    expect(badge.className).toContain('text-violet-700');
  });

  it('applies red classes for error status', () => {
    const { container } = render(<StatusBadge status="error" />);
    const badge = container.firstElementChild!;
    expect(badge.className).toContain('bg-red-50');
    expect(badge.className).toContain('text-red-700');
  });

  it('includes dot indicator', () => {
    const { container } = render(<StatusBadge status="processing" />);
    const dot = container.querySelector('.rounded-full');
    expect(dot).toBeInTheDocument();
  });

  it('accepts custom className', () => {
    const { container } = render(<StatusBadge status="verified" className="my-class" />);
    expect(container.firstElementChild!.className).toContain('my-class');
  });
});
