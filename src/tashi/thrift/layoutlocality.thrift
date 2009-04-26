struct BlockLocation {
       list<string> hosts,           // hostnames of data nodes
       list<i32> ports,              // ports for data nodes
       list<string> names,           // hostname:port of data nodes
       i64 blocknum,
       i64 offset,
       i64 length
}

struct Pathname {
       string pathname
}

exception FileNotFoundException {
       string message
}

service layoutservice {
       list <BlockLocation> getFileBlockLocations(1:Pathname path, 2:i64 offset, 3:i64 length)
                            throws (1:FileNotFoundException ouch),
}

service localityservice {
       list <list<double>> getHopCountMatrix(1:list<string> sourceHosts, 2:list<string> destHosts),
}
