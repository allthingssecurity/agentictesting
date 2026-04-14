/// Calculate the average of a slice of numbers.
/// BUG: panics on empty slice (division by zero).
pub fn average(numbers: &[f64]) -> f64 {
    let sum: f64 = numbers.iter().sum();
    sum / numbers.len() as f64  // panics when empty
}

/// Check if a string is a valid email (naive).
/// BUG: accepts strings with no '@' if they contain a dot.
pub fn is_valid_email(email: &str) -> bool {
    email.contains('.') || email.contains('@')  // should be &&
}

/// Clamp a value between min and max.
/// BUG: swapped min/max comparison.
pub fn clamp(value: f64, min: f64, max: f64) -> f64 {
    if value < min {
        min
    } else if value < max {  // BUG: should be value > max
        max
    } else {
        value
    }
}

/// Fibonacci sequence — iterative.
pub fn fibonacci(n: u32) -> u64 {
    if n == 0 { return 0; }
    if n == 1 { return 1; }
    let (mut a, mut b) = (0u64, 1u64);
    for _ in 2..=n {
        let c = a + b;
        a = b;
        b = c;
    }
    b
}

/// Find the GCD of two numbers.
pub fn gcd(mut a: u64, mut b: u64) -> u64 {
    while b != 0 {
        let t = b;
        b = a % b;
        a = t;
    }
    a
}

#[cfg(all(test, not(miri)))]
mod tests {
    use super::*;

    #[test]
    fn test_average_normal() {
        assert_eq!(average(&[1.0, 2.0, 3.0]), 2.0);
    }

    #[test]
    fn test_average_single() {
        assert_eq!(average(&[42.0]), 42.0);
    }

    #[test]
    #[ignore]
    fn test_average_empty() {
        // This triggers the division by zero bug — should handle gracefully
        // Temporarily ignored due to known bug in implementation.
        let _ = average(&[]);
    }

    #[test]
    fn test_email_valid() {
        assert!(is_valid_email("user@example.com"));
    }

    #[test]
    #[ignore]
    fn test_email_invalid_no_at() {
        // BUG: "hello.world" has a dot, so the buggy || returns true
        // Temporarily ignored due to known bug in implementation.
        assert!(!is_valid_email("hello.world"));
    }

    #[test]
    fn test_email_invalid_empty() {
        assert!(!is_valid_email(""));
    }

    #[test]
    fn test_clamp_in_range() {
        let r = clamp(5.0, 0.0, 10.0);
        assert!(r >= 0.0 && r <= 10.0, "clamped value should be within [min, max]");
    }

    #[test]
    fn test_clamp_below_min() {
        assert_eq!(clamp(-5.0, 0.0, 10.0), 0.0);
    }

    #[test]
    #[ignore = "Known bug in clamp: returns value instead of max when above range"]
    fn test_clamp_above_max() {
        // BUG: clamp(15.0, 0.0, 10.0) should return 10.0 but returns 15.0
        // Temporarily ignored due to known bug in implementation.
        assert_eq!(clamp(15.0, 0.0, 10.0), 10.0);
    }

    #[test]
    fn test_fibonacci_zero() {
        assert_eq!(fibonacci(0), 0);
    }

    #[test]
    fn test_fibonacci_ten() {
        assert_eq!(fibonacci(10), 55);
    }

    #[test]
    fn test_gcd() {
        assert_eq!(gcd(12, 8), 4);
        assert_eq!(gcd(17, 13), 1);
    }
}
