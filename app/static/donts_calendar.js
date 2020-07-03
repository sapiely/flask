function showMe (box, name, startCheck) {

    var chboxs = document.getElementsByName(name);
    var vis = "none";
    if(chboxs[0].checked && !startCheck){
        vis = "block";
    }else if (!chboxs[0].checked && startCheck) {
        vis = "block";
    }
    document.getElementById(box).style.display = vis;
}
function delete_all() {
    if (confirm("{{ _('Delete all events?') }}")){
        if (confirm("{{ _('Are you sure?') }}")){
                    $.post('/calendar_delete_all', {
                    }).done(function() {
                        window.location.href = "calendar"
                    }).fail(function() {
                        $(eventObj.id).text("{{ _('Error: Could not contact server.') }}");
                    });
                    }
    }
}
function adding () {
    var name = document.querySelector('input[type="text"]').value;
    var dateSStr = document.querySelector('input[id="dateStart"]').value;
    var dateEStr = document.querySelector('input[id="dateEnd"]').value;
    var color = document.querySelector('input[id="colortext"]').value;
    var url = document.querySelector('input[id="url"]').value;
    var dateStart = moment(dateSStr);
    var dateEnd = moment(dateEStr);
    ( async () =>{
    if (dateStart.isValid() && dateEnd.isValid()) {
        await addingDB(name, moment(dateSStr).format(), end=moment(dateEnd).format(), color, 0, url);
    } else if (dateStart.isValid() && !dateEnd.isValid()) {
        await addingDB(name, moment(dateSStr).format(), "", color, 1, url);
    } 
    else {
        alert("{{ _('Failed.') }}")
    };
    setTimeout(() => { $('#calendar').fullCalendar('refetchEvents'); }, 100);
    }
    )();
}
function addingDB(title, start, end="", color , all, url="") {
$.post('/calendar_add', {
    title: title,
    start: start,
    end: end,
    color: color,
    url: url,
    allDay: all
}).done(function(response) {
    window.id_of_event = response['id']
    return window.id_of_event
}).fail(function() {
    $(event_id).text("{{ _('Error: Could not contact server.') }}");
});
return window.id_of_event
}
$(document).ready(function() {
    $('#calendar').fullCalendar({
        header: {
            left: 'prev,next today, addEventButton',
            center: 'title',
            right: 'month,agendaWeek,agendaDay'
        },
        buttonText: {
            today:    "{{ _('Today') }}",
            month:    "{{ _('Month') }}",
            week:     "{{ _('Week') }}",
            day:      "{{ _('Day') }}",
        },
        contentHeight: 500,
        locale: "{{ _('ru') }}",
        fixedWeekCount: false,
        navLinks: true,
        editable: true,
        eventLimit: true,
        events: {
            url: 'data',
            error: function() {
                $('#script-warning').show();
            }
        },
        loading: function(bool) {
            $('#loading').toggle(bool);
        },
        customButtons:{
        },
        eventClick:  function(event, jsEvent, view) {
            if (document.getElementById('delete_mode').checked){
            $('#modalBody').html("{{ _('Event *') }}" + event.title + "{{ _('* will be deleted!') }}");
            $('#delete_btn').attr('onclick', "delete_event("+event.id+")");
            $('#calendarModal').modal();
            } else if (!document.getElementById('delete_mode').checked && event.url) {
                window.open(event.url, "_blank");
                return false;
            }
            return false;
        },	
    });
});
function delete_event(event_id) {
    if (document.getElementById('delete_mode').checked){
        $.post('/calendar_delete', {
            id: event_id,
        }).done(function() {
            $('#calendar').fullCalendar('removeEvents', event_id)
        }).fail(function() {
            $(event_id).text("{{ _('Error: Could not contact server.') }}");
        });
    
        return false;
        }
}