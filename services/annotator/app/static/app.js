/**
 * Annotator application JavaScript
 */

console.log('Parkour Spotter Annotator loaded');

async function addAnnotation() {
    const h3Index = document.getElementById('h3-index').value;
    const notes = document.getElementById('notes').value;
    const rating = parseFloat(document.getElementById('rating').value) || 0;

    if (!h3Index) {
        alert('Please enter an H3 index');
        return;
    }

    try {
        const response = await fetch('/spots', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                h3_index: h3Index,
                notes: notes,
                rating: rating,
            }),
        });

        if (response.ok) {
            const spot = await response.json();
            console.log('Annotation created:', spot);
            loadAnnotations();
        } else {
            console.error('Failed to create annotation');
        }
    } catch (error) {
        console.error('Error creating annotation:', error);
    }
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

    let html = '<h3>Annotations</h3><ul>';
    spots.forEach(spot => {
        html += `<li>
            <strong>${spot.h3_index}</strong><br>
            ${spot.notes}<br>
            Rating: ${spot.rating}/5
        </li>`;
    });
    html += '</ul>';
    container.innerHTML = html;
}

document.addEventListener('DOMContentLoaded', () => {
    loadAnnotations();
});
