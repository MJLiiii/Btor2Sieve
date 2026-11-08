(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x802 (and (distinct s_7 (_ bv255 8)) true)))
(not $x802)))
(check-sat)
