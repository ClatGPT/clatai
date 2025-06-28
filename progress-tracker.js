// CLAT.GPT.1 Progress Tracker
// Shared progress tracking functionality for all pages

// Save progress data to localStorage
function saveProgress(section, subcategory, score, total, additionalData = {}) {
    try {
        // Load existing progress
        const progressData = JSON.parse(localStorage.getItem('clatProgress') || '[]');
        
        // Create new progress entry
        const progressEntry = {
            id: Date.now(), // Unique ID
            section: section,
            subcategory: subcategory || '',
            score: score,
            total: total,
            percentage: Math.round((score / total) * 100),
            date: new Date().toISOString(),
            timestamp: Date.now(),
            ...additionalData
        };
        
        // Add to progress array
        progressData.push(progressEntry);
        
        // Keep only last 100 entries to prevent localStorage overflow
        if (progressData.length > 100) {
            progressData.splice(0, progressData.length - 100);
        }
        
        // Save back to localStorage
        localStorage.setItem('clatProgress', JSON.stringify(progressData));
        
        console.log('✅ Progress saved:', progressEntry);
        
        // Update streak if this is a new day
        updateStreak();
        
        return true;
    } catch (error) {
        console.error('❌ Error saving progress:', error);
        return false;
    }
}

// Update daily streak
function updateStreak() {
    try {
        const lastVisit = localStorage.getItem('lastVisitDate');
        const today = new Date().toDateString();
        const currentStreak = parseInt(localStorage.getItem('dailyStreak') || '0');
        
        if (lastVisit !== today) {
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            
            if (lastVisit === yesterday.toDateString()) {
                // Consecutive day
                const newStreak = currentStreak + 1;
                localStorage.setItem('dailyStreak', newStreak.toString());
                console.log('🔥 Streak updated:', newStreak);
            } else {
                // New streak
                localStorage.setItem('dailyStreak', '1');
                console.log('🔥 New streak started');
            }
            
            localStorage.setItem('lastVisitDate', today);
        }
    } catch (error) {
        console.error('❌ Error updating streak:', error);
    }
}

// Get progress statistics
function getProgressStats() {
    try {
        const progressData = JSON.parse(localStorage.getItem('clatProgress') || '[]');
        
        if (progressData.length === 0) {
            return {
                totalTests: 0,
                averageScore: 0,
                sectionStats: {
                    'Legal Reasoning': { percentage: 0, count: 0 },
                    'Logical Reasoning': { percentage: 0, count: 0 },
                    'English Language': { percentage: 0, count: 0 },
                    'General Knowledge': { percentage: 0, count: 0 },
                    'Quantitative Techniques': { percentage: 0, count: 0 }
                }
            };
        }
        
        // Calculate overall stats
        const totalTests = progressData.length;
        const averageScore = Math.round(
            progressData.reduce((sum, test) => sum + test.percentage, 0) / totalTests
        );
        
        // Calculate section-wise stats
        const sectionStats = {
            'Legal Reasoning': { total: 0, correct: 0, count: 0 },
            'Logical Reasoning': { total: 0, correct: 0, count: 0 },
            'English Language': { total: 0, correct: 0, count: 0 },
            'General Knowledge': { total: 0, correct: 0, count: 0 },
            'Quantitative Techniques': { total: 0, correct: 0, count: 0 }
        };
        
        progressData.forEach(test => {
            const section = mapSectionName(test.section);
            if (sectionStats[section]) {
                sectionStats[section].total += test.total;
                sectionStats[section].correct += test.score;
                sectionStats[section].count += 1;
            }
        });
        
        // Calculate percentages
        Object.keys(sectionStats).forEach(section => {
            const stats = sectionStats[section];
            stats.percentage = stats.count > 0 ? Math.round((stats.correct / stats.total) * 100) : 0;
        });
        
        return {
            totalTests,
            averageScore,
            sectionStats
        };
    } catch (error) {
        console.error('❌ Error getting progress stats:', error);
        return {
            totalTests: 0,
            averageScore: 0,
            sectionStats: {}
        };
    }
}

// Map section names to standardized names
function mapSectionName(section) {
    const sectionMap = {
        'legal': 'Legal Reasoning',
        'legal reasoning': 'Legal Reasoning',
        'logical': 'Logical Reasoning',
        'logical reasoning': 'Logical Reasoning',
        'english': 'English Language',
        'english language': 'English Language',
        'gk': 'General Knowledge',
        'general knowledge': 'General Knowledge',
        'quantitative': 'Quantitative Techniques',
        'quantitative techniques': 'Quantitative Techniques',
        'qt': 'Quantitative Techniques',
        'math': 'Quantitative Techniques',
        'mathematics': 'Quantitative Techniques'
    };
    
    return sectionMap[section.toLowerCase()] || section;
}

// Get recent activity
function getRecentActivity(limit = 5) {
    try {
        const progressData = JSON.parse(localStorage.getItem('clatProgress') || '[]');
        
        return progressData
            .sort((a, b) => new Date(b.date) - new Date(a.date))
            .slice(0, limit);
    } catch (error) {
        console.error('❌ Error getting recent activity:', error);
        return [];
    }
}

// Clear all progress data
function clearProgress() {
    try {
        localStorage.removeItem('clatProgress');
        console.log('🗑️ Progress data cleared');
        return true;
    } catch (error) {
        console.error('❌ Error clearing progress:', error);
        return false;
    }
}

// Export progress data
function exportProgress() {
    try {
        const progressData = JSON.parse(localStorage.getItem('clatProgress') || '[]');
        const stats = getProgressStats();
        
        const exportData = {
            exportDate: new Date().toISOString(),
            stats: stats,
            progress: progressData
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `clat-progress-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        console.log('📤 Progress exported');
        return true;
    } catch (error) {
        console.error('❌ Error exporting progress:', error);
        return false;
    }
}

// Import progress data
function importProgress(jsonData) {
    try {
        const data = JSON.parse(jsonData);
        
        if (data.progress && Array.isArray(data.progress)) {
            localStorage.setItem('clatProgress', JSON.stringify(data.progress));
            console.log('📥 Progress imported:', data.progress.length, 'entries');
            return true;
        } else {
            throw new Error('Invalid progress data format');
        }
    } catch (error) {
        console.error('❌ Error importing progress:', error);
        return false;
    }
}

// Get username from localStorage
function getUsername() {
    return localStorage.getItem('$username') || 'Student';
}

// Set username in localStorage
function setUsername(username) {
    localStorage.setItem('$username', username);
    console.log('👤 Username set:', username);
}

// Get current streak
function getCurrentStreak() {
    return parseInt(localStorage.getItem('dailyStreak') || '0');
}

// Initialize progress tracking
function initProgressTracking() {
    // Update streak on page load
    updateStreak();
    
    // Set default username if not exists
    if (!localStorage.getItem('$username')) {
        setUsername('Student');
    }
    
    console.log('🚀 Progress tracking initialized');
}

// Auto-initialize when script loads
if (typeof window !== 'undefined') {
    initProgressTracking();
} 