(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x221 (bvuge s_7 (_ bv128 8))))
(not $x221)))
(check-sat)
