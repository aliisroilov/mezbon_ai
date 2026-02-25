import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, Upload, FileImage } from "lucide-react";
import dayjs from "dayjs";
import { faqAPI, contentAPI } from "../../api/client";
import {
  Card,
  Button,
  Badge,
  Modal,
  Input,
  Select,
  Textarea,
  Tabs,
  LoadingSpinner,
} from "../../components/ui";
import type { FAQ, Announcement, Language } from "../../types";

export function ContentPage() {
  const [activeTab, setActiveTab] = useState("faq");

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Content</h1>
      <Tabs
        tabs={[
          { id: "faq", label: "FAQ" },
          { id: "announcements", label: "Announcements" },
          { id: "media", label: "Media" },
        ]}
        activeTab={activeTab}
        onChange={setActiveTab}
      />

      {activeTab === "faq" && <FAQSection />}
      {activeTab === "announcements" && <AnnouncementsSection />}
      {activeTab === "media" && <MediaSection />}
    </div>
  );
}

// === FAQ Section ===
function FAQSection() {
  const queryClient = useQueryClient();
  const [langFilter, setLangFilter] = useState<string>("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<FAQ | null>(null);

  const { data: faqs, isLoading } = useQuery<FAQ[]>({
    queryKey: ["faqs", langFilter],
    queryFn: () => faqAPI.list({ language: langFilter || undefined }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => faqAPI.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["faqs"] }),
  });

  return (
    <>
      <Card>
        <div className="flex items-center justify-between mb-4">
          <div className="w-36">
            <Select
              options={[
                { value: "", label: "All Languages" },
                { value: "uz", label: "Uzbek" },
                { value: "ru", label: "Russian" },
                { value: "en", label: "English" },
              ]}
              value={langFilter}
              onChange={(e) => setLangFilter(e.target.value)}
            />
          </div>
          <Button
            icon={<Plus className="h-4 w-4" />}
            size="sm"
            onClick={() => { setEditing(null); setShowForm(true); }}
          >
            Add FAQ
          </Button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-10">
            <LoadingSpinner />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left">
                  <th className="pb-3 pr-4 font-medium text-slate-500">Question</th>
                  <th className="pb-3 pr-4 font-medium text-slate-500 w-20">Lang</th>
                  <th className="pb-3 pr-4 font-medium text-slate-500 w-20">Order</th>
                  <th className="pb-3 font-medium text-slate-500 w-24">Actions</th>
                </tr>
              </thead>
              <tbody>
                {(faqs ?? []).map((faq) => (
                  <tr key={faq.id} className="border-b border-slate-100 last:border-0">
                    <td className="py-3 pr-4">
                      <p className="font-medium text-slate-900">{faq.question}</p>
                      <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">
                        {faq.answer}
                      </p>
                    </td>
                    <td className="py-3 pr-4">
                      <Badge>{faq.language.toUpperCase()}</Badge>
                    </td>
                    <td className="py-3 pr-4 text-slate-600">{faq.sort_order}</td>
                    <td className="py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => { setEditing(faq); setShowForm(true); }}
                          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm("Delete this FAQ?")) deleteMutation.mutate(faq.id);
                          }}
                          className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editing ? "Edit FAQ" : "Add FAQ"}
      >
        <FAQForm
          faq={editing}
          onSuccess={() => {
            setShowForm(false);
            queryClient.invalidateQueries({ queryKey: ["faqs"] });
          }}
        />
      </Modal>
    </>
  );
}

function FAQForm({ faq, onSuccess }: { faq: FAQ | null; onSuccess: () => void }) {
  const [question, setQuestion] = useState(faq?.question ?? "");
  const [answer, setAnswer] = useState(faq?.answer ?? "");
  const [language, setLanguage] = useState<Language>(faq?.language ?? "uz");
  const [sortOrder, setSortOrder] = useState(String(faq?.sort_order ?? 0));

  const mutation = useMutation({
    mutationFn: () => {
      const data = { question, answer, language, sort_order: parseInt(sortOrder) || 0 };
      return faq ? faqAPI.update(faq.id, data) : faqAPI.create(data);
    },
    onSuccess,
  });

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}
      className="space-y-4"
    >
      <Input
        label="Question"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        required
      />
      <Textarea
        label="Answer"
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        rows={4}
        required
      />
      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Language"
          value={language}
          onChange={(e) => setLanguage(e.target.value as Language)}
          options={[
            { value: "uz", label: "Uzbek" },
            { value: "ru", label: "Russian" },
            { value: "en", label: "English" },
          ]}
        />
        <Input
          label="Sort Order"
          type="number"
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value)}
        />
      </div>
      {mutation.error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {(mutation.error as Error).message}
        </div>
      )}
      <div className="flex justify-end">
        <Button type="submit" loading={mutation.isPending}>
          {faq ? "Update" : "Create"}
        </Button>
      </div>
    </form>
  );
}

// === Announcements Section ===
function AnnouncementsSection() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Announcement | null>(null);

  const { data: announcements, isLoading } = useQuery<Announcement[]>({
    queryKey: ["announcements"],
    queryFn: contentAPI.announcements.list,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => contentAPI.announcements.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["announcements"] }),
  });

  return (
    <>
      <Card>
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-slate-500">
            {(announcements ?? []).length} announcement(s)
          </p>
          <Button
            icon={<Plus className="h-4 w-4" />}
            size="sm"
            onClick={() => { setEditing(null); setShowForm(true); }}
          >
            Add Announcement
          </Button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-10">
            <LoadingSpinner />
          </div>
        ) : (
          <div className="space-y-3">
            {(announcements ?? []).map((ann) => (
              <div
                key={ann.id}
                className="rounded-lg border border-slate-200 p-4"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-medium text-slate-900">{ann.title}</h4>
                    <p className="text-sm text-slate-600 mt-1">{ann.body}</p>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge>{ann.language.toUpperCase()}</Badge>
                      <span className="text-xs text-slate-400">
                        {dayjs(ann.active_from).format("DD MMM")} — {dayjs(ann.active_to).format("DD MMM YYYY")}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => { setEditing(ann); setShowForm(true); }}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm("Delete?")) deleteMutation.mutate(ann.id);
                      }}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editing ? "Edit Announcement" : "Add Announcement"}
      >
        <AnnouncementForm
          announcement={editing}
          onSuccess={() => {
            setShowForm(false);
            queryClient.invalidateQueries({ queryKey: ["announcements"] });
          }}
        />
      </Modal>
    </>
  );
}

function AnnouncementForm({
  announcement,
  onSuccess,
}: {
  announcement: Announcement | null;
  onSuccess: () => void;
}) {
  const [title, setTitle] = useState(announcement?.title ?? "");
  const [body, setBody] = useState(announcement?.body ?? "");
  const [language, setLanguage] = useState<Language>(announcement?.language ?? "uz");
  const [activeFrom, setActiveFrom] = useState(
    announcement?.active_from ? dayjs(announcement.active_from).format("YYYY-MM-DD") : dayjs().format("YYYY-MM-DD"),
  );
  const [activeTo, setActiveTo] = useState(
    announcement?.active_to ? dayjs(announcement.active_to).format("YYYY-MM-DD") : dayjs().add(7, "day").format("YYYY-MM-DD"),
  );

  const mutation = useMutation({
    mutationFn: () => {
      const data = { title, body, language, active_from: activeFrom, active_to: activeTo };
      return announcement
        ? contentAPI.announcements.update(announcement.id, data)
        : contentAPI.announcements.create(data);
    },
    onSuccess,
  });

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}
      className="space-y-4"
    >
      <Input
        label="Title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        required
      />
      <Textarea
        label="Body"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={4}
        required
      />
      <Select
        label="Language"
        value={language}
        onChange={(e) => setLanguage(e.target.value as Language)}
        options={[
          { value: "uz", label: "Uzbek" },
          { value: "ru", label: "Russian" },
          { value: "en", label: "English" },
        ]}
      />
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Active From"
          type="date"
          value={activeFrom}
          onChange={(e) => setActiveFrom(e.target.value)}
        />
        <Input
          label="Active To"
          type="date"
          value={activeTo}
          onChange={(e) => setActiveTo(e.target.value)}
        />
      </div>
      {mutation.error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {(mutation.error as Error).message}
        </div>
      )}
      <div className="flex justify-end">
        <Button type="submit" loading={mutation.isPending}>
          {announcement ? "Update" : "Create"}
        </Button>
      </div>
    </form>
  );
}

// === Media Section ===
function MediaSection() {
  const queryClient = useQueryClient();

  const { data: media, isLoading } = useQuery({
    queryKey: ["media"],
    queryFn: contentAPI.media.list,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => contentAPI.media.upload(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["media"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (name: string) => contentAPI.media.delete(name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["media"] }),
  });

  function handleFileSelect() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*,video/*";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) uploadMutation.mutate(file);
    };
    input.click();
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-slate-500">
          {(media ?? []).length} file(s)
        </p>
        <Button
          icon={<Upload className="h-4 w-4" />}
          size="sm"
          onClick={handleFileSelect}
          loading={uploadMutation.isPending}
        >
          Upload
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-10">
          <LoadingSpinner />
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {(media ?? []).map((file) => (
            <div
              key={file.name}
              className="group relative rounded-lg border border-slate-200 overflow-hidden"
            >
              <div className="aspect-square bg-slate-100 flex items-center justify-center">
                {file.url.match(/\.(jpg|jpeg|png|gif|webp)$/i) ? (
                  <img
                    src={file.url}
                    alt={file.name}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <FileImage className="h-8 w-8 text-slate-400" />
                )}
              </div>
              <div className="p-2">
                <p className="text-xs font-medium text-slate-700 truncate">
                  {file.name}
                </p>
                <p className="text-xs text-slate-400">
                  {(file.size / 1024).toFixed(0)} KB
                </p>
              </div>
              <button
                onClick={() => {
                  if (confirm("Delete this file?")) deleteMutation.mutate(file.name);
                }}
                className="absolute top-1 right-1 rounded-full bg-red-500 p-1 text-white opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
