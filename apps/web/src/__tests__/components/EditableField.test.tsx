import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EditableField } from '@/components/EditableField';

describe('EditableField', () => {
  it('renders label and value', () => {
    render(
      <EditableField label="Invoice Number" value="INV-001" onChange={() => {}} />
    );
    expect(screen.getByText('Invoice Number')).toBeInTheDocument();
    expect(screen.getByDisplayValue('INV-001')).toBeInTheDocument();
  });

  it('renders empty string for null value', () => {
    render(
      <EditableField label="Date" value={null} onChange={() => {}} />
    );
    const input = screen.getByRole('textbox');
    expect(input).toHaveValue('');
  });

  it('calls onChange when user types', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(
      <EditableField label="Number" value="" onChange={handleChange} />
    );
    const input = screen.getByRole('textbox');
    await user.type(input, 'A');
    expect(handleChange).toHaveBeenCalledWith('A');
  });

  it('disables input when disabled prop is true', () => {
    render(
      <EditableField label="Field" value="test" onChange={() => {}} disabled />
    );
    expect(screen.getByDisplayValue('test')).toBeDisabled();
  });

  it('shows confidence badge when confidence is provided', () => {
    render(
      <EditableField label="Field" value="val" onChange={() => {}} confidence={85} />
    );
    expect(screen.getByText('confidenceReliable')).toBeInTheDocument();
  });

  it('does not show confidence badge when confidence is null', () => {
    const { container } = render(
      <EditableField label="Field" value="val" onChange={() => {}} confidence={null} />
    );
    // Null confidence renders em-dash, not a label
    expect(container.textContent).not.toContain('confidenceReliable');
  });

  it('renders correct input type', () => {
    const { container } = render(
      <EditableField label="Date" value="2026-01-01" onChange={() => {}} type="date" />
    );
    const input = container.querySelector('input');
    expect(input).toHaveAttribute('type', 'date');
  });
});
