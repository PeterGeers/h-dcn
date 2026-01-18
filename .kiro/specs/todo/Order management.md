Order management as subset of productmanagement. All activities after payment is received from stripe or alikes.

- Taking the order with status paid
- Update status from paid to in progress
- send statusupdate e-mail to client
- Update stock table (fast reporting, only negative quantity and value) only positive quantity and value
- Collect the products (physical) check products and product types
- Packages them
- Print package note
- Print address label
- Bring/Collect to distributor
- Change status from progress to send
- send email to client confirmation on status update
- Handle issues in case client complains
- Stock management
  -- Add incoming stock to stock table (sane table and structure as only positive quantity and value) only positive quantity and value
