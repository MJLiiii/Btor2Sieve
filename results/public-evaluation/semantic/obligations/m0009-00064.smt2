(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x401 (bvule s_6 (_ bv7 4))))
(not $x401)))
(check-sat)
