(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x114 (bvule s_4 (_ bv1 4))))
(not $x114)))
(check-sat)
