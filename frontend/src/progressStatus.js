// Progress status shared by document sessions and Quick Captures.
// A missing value (older rows) means the work is still in progress.
export const PROGRESS_STATUSES = [
  { value: "in_progress", label: "In progress" },
  { value: "done", label: "Done" },
  { value: "published", label: "Published" },
];

export const progressStatusOf = (item) => item?.progress_status || "in_progress";

export const progressLabel = (status) =>
  PROGRESS_STATUSES.find((option) => option.value === status)?.label || "In progress";
