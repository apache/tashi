default: install
	@echo Done

install: checkroot theconvertz manpage livesupportdebs

theconvertz:
	@echo Install convertz...
	@if [ ! -e /usr/local/sbin/convertz ]; then echo No file, installing...; cp convertz /usr/local/sbin; chmod 700 /usr/local/sbin/convertz; else echo Got old file, removing old file then install a new one...; rm /usr/local/sbin/convertz; cp convertz /usr/local/sbin; chmod 700 /usr/local/sbin/convertz; fi

uninstall: checkroot
	@echo Removing convertz and its companions...
	@if [ -f /usr/local/sbin/convertz ]; then echo Removing convertz; rm /usr/local/sbin/convertz; else echo No file found; fi
	@if [ -f /usr/local/man/man8/convertz.8.gz ]; then echo Removing convertz manual; rm /usr/local/man/man8/convertz.8.gz; else echo No manual found; fi
	@if [ -d /var/www/live-boot-support ]; then echo Removing Debian Live Packages; rm -rf /var/www/live-boot-support; else echo No Debian Live Packages found; fi

manpage:
	@echo Install convertz manual...
	@if [ ! -d /usr/local/man/man8 ]; then echo No man8 folder, creating man8 folder then install manual...; mkdir -p /usr/local/man/man8; gzip -c convertz.8 > /usr/local/man/man8/convertz.8.gz; elif [ -f /usr/local/man/man8/convertz.8.gz ]; then echo Got old manual, removing old manual then install a new one...; rm /usr/local/man/man8/convertz.8.gz; gzip -c convertz.8 > /usr/local/man/man8/convertz.8.gz; else echo No manual; echo Installing a manual...; gzip -c convertz.8 > /usr/local/man/man8/convertz.8.gz; fi; fi

livesupportdebs:
	@echo Install Debian Live Packages...
	@if [ ! -d /var/www/live-boot-support ]; then echo No live-boot-support, copying with folder...; cp -r ./live-boot-support /var/www; else echo Copying debs over...; cp ./live-boot-support/*.deb /var/www/live-boot-support/; fi

checkroot:
	@if [ `id -u` -eq 0 ]; then echo OK to proceed...; else echo You have to be root to run this; exit 1; fi
