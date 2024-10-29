$(document).ready(function () {
    $('#csvTable').DataTable({
        "paging": false,  // Enable pagination
        "pageLength": 10,  // Items per page
        "lengthChange": false,  // Disable page length dropdown
        "searching": true,  // Enable search
        "ordering": true,  // Enable column ordering
        "autoWidth": false,
        "responsive": true,
        "info": false,  // Hide table info (e.g., "Showing 1 to 10 of 57 entries")
        "initComplete": function () {
                // Style the search input using Tailwind CSS classes
                let searchBox = $('#csvTable_filter input');
                searchBox.addClass('border border-gray-300 my-2 mx-1 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent');

                // Style the search label
                let searchLabel = $('#csvTable_filter label');
                searchLabel.addClass('block text-gray-700 font-medium mb-2');
            }
    });
});