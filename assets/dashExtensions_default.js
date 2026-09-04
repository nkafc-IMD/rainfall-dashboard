window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature) {
            return {
                fillColor: feature.properties.color,
                color: feature.properties.borderColor || '#8a5a1e',
                weight: feature.properties.borderWeight !== undefined ? feature.properties.borderWeight :
                    (feature.properties.color === '#e07b1a' ? 2.5 : 1),
                fillOpacity: feature.properties.fillOpacity
            };
        },
        function1: function(feature) {
            return {
                fillColor: feature.properties.color,
                color: '#666666',
                weight: 1,
                fillOpacity: feature.properties.fillOpacity
            };
        }
    }
});