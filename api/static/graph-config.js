// Graph Configuration - Colors and Settings
window.GraphConfig = (function() {
    'use strict';
    
    // ===== VISUAL CONFIG =====
    const VISUAL = {
        nodeRadius: 12,
        labelFontSize: 16,
        linkWidth: 2,
        hoverNodeRadius: 15,
        hoverLinkWidth: 4
    };
    
    // ===== SIMULATION CONFIG =====
    const SIMULATION = {
        linkDistance: 100,
        linkStrength: 0.3,
        chargeStrength: -400,
        centerStrength: 0.1,
        collisionRadius: 25,
        alphaTarget: 0.3,
        alphaDecay: 0.01
    };
    
    // ===== PREDEFINED COLORS (Jaskrawe na ciemnym tle) =====
    const PREDEFINED_COLORS = {
        // Literary domain
        'CHARACTER': '#FF1493',      // Fuksja
        'EMOTIONAL_STATE': '#00FF7F', // Limonkowa
        'LOCATION': '#FF4500',       // Chińska czerwień
        'OBJECT': '#FFD700',         // Mocna żółć
        'EVENT': '#00CED1',          // Turkus
        'DIALOG': '#00FFFF',         // Cyjan
        
        // Common Polish NER types
        'OSOBA': '#FF1493',          // Fuksja
        'MIEJSCE': '#00FF7F',        // Limonkowa
        'ORGANIZACJA': '#FF4500',    // Chińska czerwień
        'PRZEDMIOT': '#FFD700',      // Mocna żółć
        'WYDARZENIE': '#00CED1',     // Turkus
        'KONCEPCJA': '#00FFFF',      // Cyjan
        'CZAS': '#9D4EDD',           // Fioletowy
        'SCENA': '#F72585',          // Różowy
        'ZWROTKA': '#7209B7',        // Fiolet
        'TERMIN_ZDEFINIOWANY': '#20B2AA', // LightSeaGreen
        'DEFINICJA': '#FF6347',      // Tomato
        'WYŁĄCZENIE_Z_UMOWY': '#FFB6C1' // LightPink
    };
    
    // ===== ADDITIONAL VIBRANT COLORS =====
    const ADDITIONAL_COLORS = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
        '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
        '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D7DBDD',
        '#FF69B4', '#00FA9A', '#FF4500', '#FFD700', '#1E90FF',
        '#FF1493', '#00CED1', '#FF6347', '#32CD32', '#8A2BE2'
    ];
    
    // ===== STATE =====
    let entityTypes = [];
    let relationshipTypes = [];
    let entityColors = { ...PREDEFINED_COLORS };
    
    // ===== COLOR UTILITIES =====
    function generateColorForType(type) {
        if (entityColors[type]) {
            return entityColors[type];
        }
        
        // Generate deterministic color based on type name
        const hash = hashString(type);
        const colorIndex = hash % ADDITIONAL_COLORS.length;
        const color = ADDITIONAL_COLORS[colorIndex];
        
        entityColors[type] = color;
        return color;
    }
    
    function hashString(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return Math.abs(hash);
    }
    
    function dimColor(hexColor, factor = 0.4) {
        // Convert hex to RGB and dim by factor
        const hex = hexColor.replace('#', '');
        const r = parseInt(hex.substr(0, 2), 16);
        const g = parseInt(hex.substr(2, 2), 16);
        const b = parseInt(hex.substr(4, 2), 16);
        
        const dimR = Math.round(r * factor);
        const dimG = Math.round(g * factor);
        const dimB = Math.round(b * factor);
        
        return `rgb(${dimR}, ${dimG}, ${dimB})`;
    }
    
    // ===== PUBLIC API =====
    return {
        // Constants
        VISUAL,
        SIMULATION,
        
        // Color management
        getEntityColor: (type) => generateColorForType(type),
        getDimmedEntityColor: (type, factor = 0.4) => dimColor(generateColorForType(type), factor),
        getAllEntityColors: () => ({ ...entityColors }),
        
        // Type management
        setEntityTypes: (types) => {
            entityTypes = [...types];
            // Pre-generate colors for all types
            types.forEach(type => generateColorForType(type));
        },
        setRelationshipTypes: (types) => {
            relationshipTypes = [...types];
        },
        getEntityTypes: () => [...entityTypes],
        getRelationshipTypes: () => [...relationshipTypes],
        
        // Utilities
        truncateText: (text, maxLength) => {
            if (!text) return '';
            return text.length > maxLength ? text.slice(0, maxLength) + '...' : text;
        },
        
        debounce: (func, wait) => {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
    };
})();