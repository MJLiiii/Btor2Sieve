(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x1308 (and (distinct s_7 (_ bv127 8)) true)))
(not $x1308)))
(check-sat)
