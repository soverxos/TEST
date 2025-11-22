/**
 * Utility functions for displaying user information
 */

export interface UserDisplayInfo {
  first_name?: string;
  last_name?: string;
  username?: string;
}

/**
 * Get full name from user data
 * @param user User object with first_name, last_name, and optionally username
 * @returns Full name string or fallback to username or "User"
 */
export const getFullName = (user: UserDisplayInfo | null | undefined): string => {
  if (!user) return 'User';
  
  const firstName = user.first_name?.trim();
  const lastName = user.last_name?.trim();
  
  if (firstName && lastName) {
    return `${firstName} ${lastName}`;
  } else if (firstName) {
    return firstName;
  } else if (lastName) {
    return lastName;
  } else if (user.username) {
    return user.username;
  }
  
  return 'User';
};

/**
 * Get initials for avatar
 * @param user User object with first_name, last_name, and optionally username
 * @returns Initials string (e.g., "JD" for John Doe)
 */
export const getInitials = (user: UserDisplayInfo | null | undefined): string => {
  if (!user) return 'U';
  
  const firstName = user.first_name?.trim();
  const lastName = user.last_name?.trim();
  
  if (firstName && lastName) {
    return `${firstName[0]}${lastName[0]}`.toUpperCase();
  } else if (firstName) {
    return firstName[0].toUpperCase();
  } else if (lastName) {
    return lastName[0].toUpperCase();
  } else if (user.username) {
    return user.username[0].toUpperCase();
  }
  
  return 'U';
};

/**
 * Get display name with username as fallback
 * @param user User object
 * @returns Display name with username in parentheses if available
 */
export const getDisplayNameWithUsername = (user: UserDisplayInfo | null | undefined): string => {
  const fullName = getFullName(user);
  if (user?.username && fullName !== user.username) {
    return `${fullName} (@${user.username})`;
  }
  return fullName;
};

