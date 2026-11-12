Only put something in common if both server and client genuinely need it.

For your attendance tracker, I'd consider the following:

Contents	                Examples
Shared constants	        Application name, supported protocol version
Shared enums	            Scan status, message types, error codes
Shared data structures	    Scan request, scan response, student information
Shared utilities	        Formatting or validation functions used by both packages
Communication definitions	Message types and expected payload structures

For example, suppose your Raspberry Pi scanner sends a scan request to your Flask server. 
Both sides need to agree on what that message looks like.

You also don't need to force the client and server to share everything. 
For example, your SQLAlchemy Student model and a shared StudentData structure are two different things.

