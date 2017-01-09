'''
Created on 5 Jan 2017

@author: wat
'''

def log_user_access(program, extraInfo, logAll=False):
    """
    Writes to log file. Writes date, time, username, logged in flag, host name,
    program/webpage/resource identifier and additional information string. If the
    user is not logged in then the username comes from the BADC cookie. The
    'logged in' flag indicates if the user is actually logged in or if the
    username comes from the persistent cookie. If no username can be found then a 
    log record is only written if the 'logAll' flag has been set.
    
    @param program: String identifying program or page
    @param extraOnfo: String containing additional information
    @param logAll: If set then writes entry even if username cannot be determined.
    """
    
    '''TODO:
    my ($loginName, $cookieName) = get_usernames();
    
    my $userName;
    my $loggedIn = "n";
    
    if ($loginName) {
    $userName = $loginName;
    $loggedIn = "y";
    } elsif ($cookieName) {
    $userName = $cookieName;
    }
    
    if ($userName or $logAll) {
    
    #
    # Get current date and time
    #
    
    my $date = `date +'%d/%m/%y,%H:%M'`;
    chop $date;
    #
    # Get remote host address
    #
    my $host = $ENV{REMOTE_HOST};
    
    if (not $host) {
      $host = $ENV{REMOTE_ADDR};
    }
    
    unless (open LOG, ">>$LOG_FILE") {
       BADC::Report::report_error("Unable to open log file $LOG_FILE for writing");
       warn "Unable to open log file $LOG_FILE ($!)";
    }
    
    my $line = "$date,"      .
              "$userName,"   .
              "$loggedIn,"   .
              "$cookieName," .
              "$loginName,"  .
              "$host,"       .
              "$program,"    .
              "$extraInfo";
    
    print LOG "$line\n";
    
    close LOG
    '''
    
    return False
