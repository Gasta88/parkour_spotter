/**
 * Annotator application JavaScript
 */

console.log('Parkour Spotter Annotator loaded');

let debounceTimer = null;

async function fetchCellFeatures() {
    const h3Index = document.getElementById('h3-index').value.trim();

    if (!h3Index) {
        return;
    }

    try {
        const response = await fetch(`/spots/cell-feature/${h3Index}`);

        if (response.ok) {
            const data = await response.json();
            populateFeatureForm(data.features);
        } else if (response.status === 404) {
            console.log('No cell features found for this H3 index');
        } else {
            console.error('Failed to fetch cell features');
        }
    } catch (error) {
        console.error('Error fetching cell features:', error);
    }
}

function populateFeatureForm(features) {
    const categories = ['walls', 'rails', 'gaps', 'stairs', 'vaults', 'open_spaces'];

    categories.forEach(category => {
        if (features[category]) {
            const countInput = document.getElementById(`${category}-count`);
            const lengthInput = document.getElementById(`${category}-length`);
            const areaInput = document.getElementById(`${category}-area`);

            if (countInput) countInput.value = features[category].count || 0;
            if (lengthInput) lengthInput.value = features[category].total_length_m || 0;
            if (areaInput) areaInput.value = features[category].total_area_m2 || 0;
        }
    });
}

function buildFeaturesFromForm() {
    const categories = ['walls', 'rails', 'gaps', 'stairs', 'vaults', 'open_spaces'];
    const features = {};

    categories.forEach(category => {
        const countInput = document.getElementById(`${category}-count`);
        const lengthInput = document.getElementById(`${category}-length`);
        const areaInput = document.getElementById(`${category}-area`);

        const count = parseInt(countInput?.value) || 0;
        const length = parseFloat(lengthInput?.value) || 0;
        const area = parseFloat(areaInput?.value) || 0;

        if (count > 0 || length > 0 || area > 0) {
            features[category] = {
                count: count,
                total_length_m: length,
                total_area_m2: area
            };
        }
    });

    return Object.keys(features).length > 0 ? features : null;
}

function addAnnotation() {
    const h3Index = document.getElementById('h3-index').value.trim();
    const notes = document.getElementById('notes').value;
    const ratingValue = document.getElementById('rating').value;
    const rating = ratingValue ? parseInt(ratingValue) : 0;

    if (!h3Index) {
        alert('Please enter an H3 index');
        return;
    }

    if (rating < 0 || rating > 5) {
        alert('Rating must be between 0 and 5');
        return;
    }

    const features = buildFeaturesFromForm();

    fetch('/spots', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            h3_index: h3Index,
            notes: notes,
            rating: rating,
            features: features,
        }),
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        } else {
            throw new Error('Failed to create annotation');
        }
    })
    .then(spot => {
        console.log('Annotation created:', spot);
        clearForm();
        loadAnnotations();
    })
    .catch(error => {
        console.error('Error creating annotation:', error);
    });
}

function clearForm() {
    document.getElementById('h3-index').value = '';
    document.getElementById('notes').value = '';
    document.getElementById('rating').value = '';

    const categories = ['walls', 'rails', 'gaps', 'stairs', 'vaults', 'open_spaces'];
    categories.forEach(category => {
        const countInput = document.getElementById(`${category}-count`);
        const lengthInput = document.getElementById(`${category}-length`);
        const areaInput = document.getElementById(`${category}-area`);

        if (countInput) countInput.value = 0;
        if (lengthInput) lengthInput.value = 0;
        if (areaInput) areaInput.value = 0;
    });
}

async function loadAnnotations() {
    try {
        const response = await fetch('/spots');
        if (response.ok) {
            const spots = await response.json();
            renderAnnotations(spots);
        }
    } catch (error) {
        console.error('Error loading annotations:', error);
    }
}

function renderAnnotations(spots) {
    const container = document.getElementById('annotations-list');
    if (spots.length === 0) {
        container.innerHTML = '<h3>Annotations</h3><p>No annotations yet.</p>';
        return;
    }

    let html = '<h3>Annotations</h3>';
    spots.forEach(spot => {
        html += `<div class="spot-info">
            <strong>${spot.h3_index}</strong><br>
            ${spot.notes || 'No notes'}<br>
            Rating: ${spot.rating}/5<br>
            ${spot.human_score !== null ? `Human Score: ${spot.human_score}<br>` : ''}
            ${spot.features ? `Features: ${Object.keys(spot.features).join(', ')}<br>` : ''}
        </div>`;
    });
    container.innerHTML = html;
}

document.addEventListener('DOMContentLoaded', () => {
    loadAnnotations();
});
