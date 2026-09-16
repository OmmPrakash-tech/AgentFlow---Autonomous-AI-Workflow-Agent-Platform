create table workspace_guard (id integer primary key);
insert into workspace_guard (id) values (1);
create unique index projects_workspace_unique on projects(workspace_path);
