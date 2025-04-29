(function() {
  function initIncidentModal() {
    console.log('Initializing incident modal script');
    const incidentModal = new bootstrap.Modal(document.getElementById('incidentModal'));
    const modalTitle = document.getElementById('incidentModalLabel');
    const modalBody = document.getElementById('incidentModalBody');

    document.querySelectorAll('.view-incident-btn').forEach(button => {
      console.log('Attaching click listener to button with incident id:', button.getAttribute('data-incident-id'));
      button.addEventListener('click', async (e) => {
        e.preventDefault();
        const incidentId = button.getAttribute('data-incident-id');
        console.log('View button clicked for incident id:', incidentId);
        try {
          const response = await fetch(`/api/incident/${incidentId}`);
          if (!response.ok) throw new Error('Failed to fetch incident details');
          const incident = await response.json();

          modalTitle.textContent = `Incident #${incident.id}`;
          modalBody.innerHTML = `
            <p><strong>Description:</strong> ${incident.description}</p>
            <p><strong>Status:</strong> ${incident.status}</p>
            <p><strong>Report Date:</strong> ${incident.report_date}</p>
            ${incident.file_paths ? `<p><strong>Attached File:</strong> <a href="/static/uploads/${incident.file_paths}" target="_blank">View File</a></p>` : ''}
          `;

          incidentModal.show();
        } catch (error) {
          console.error('Error loading incident details:', error);
          alert('Error loading incident details.');
        }
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initIncidentModal);
  } else {
    initIncidentModal();
  }
})();
