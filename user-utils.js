// user-utils.js
function getDisplayName() {
    // Use $username from localStorage if available
    const stored = localStorage.getItem('$username');
    if (stored && stored.trim()) return stored;

    // Otherwise, fallback to Supabase user logic if available globally
    if (typeof currentUser !== 'undefined' && currentUser) {
        const fullName = currentUser.user_metadata?.full_name;
        const displayName = currentUser.user_metadata?.display_name;
        const email = currentUser.email;
        const finalName = fullName || displayName || (email ? email.split('@')[0] : 'User');
        localStorage.setItem('$username', finalName);
        return finalName;
    }
    return 'User';
} 