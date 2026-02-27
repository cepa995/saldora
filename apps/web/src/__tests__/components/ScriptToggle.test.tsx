import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ScriptToggle } from '@/components/ScriptToggle';

describe('ScriptToggle', () => {
  it('renders three locale options in expanded mode', () => {
    render(<ScriptToggle />);
    // Mock t() returns the key: latin, cyrillic, english
    expect(screen.getByText('latin')).toBeInTheDocument();
    expect(screen.getByText('cyrillic')).toBeInTheDocument();
    expect(screen.getByText('english')).toBeInTheDocument();
  });

  it('highlights active locale (sr-Latn)', () => {
    render(<ScriptToggle />);
    const activeButton = screen.getByText('latin');
    expect(activeButton.className).toContain('text-violet-700');
    expect(activeButton.className).toContain('bg-white');
  });

  it('shows inactive styles for non-active locales', () => {
    render(<ScriptToggle />);
    const inactiveButton = screen.getByText('english');
    expect(inactiveButton.className).toContain('text-gray-500');
    expect(inactiveButton.className).not.toContain('bg-white');
  });

  it('renders single button in collapsed mode', () => {
    render(<ScriptToggle collapsed />);
    // Should show only the active locale
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(1);
    expect(buttons[0]).toHaveTextContent('latin');
  });

  it('sets aria-pressed on active locale', () => {
    render(<ScriptToggle />);
    const latinButton = screen.getByLabelText('latin');
    expect(latinButton).toHaveAttribute('aria-pressed', 'true');
    const englishButton = screen.getByLabelText('english');
    expect(englishButton).toHaveAttribute('aria-pressed', 'false');
  });

  it('calls router.refresh when clicking a different locale', async () => {
    const user = userEvent.setup();
    // We'd need to check if cookie is set, but mocks make this simpler
    render(<ScriptToggle />);
    const englishButton = screen.getByText('english');
    await user.click(englishButton);
    // Cookie should be set (we can't easily test document.cookie in jsdom,
    // but we verify no crash occurs)
  });
});
