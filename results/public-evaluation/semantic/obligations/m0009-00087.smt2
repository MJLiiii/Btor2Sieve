(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x206 (bvuge s_7 (_ bv127 8))))
(not $x206)))
(check-sat)
